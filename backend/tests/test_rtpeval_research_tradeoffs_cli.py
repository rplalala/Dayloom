"""Offline installed generation tradeoff acceptance."""

import json

import pytest

from backend.tests.test_rtpeval_research_population_cli import add_attempt, save

pytest_plugins = ("backend.tests.test_rtpeval_research_population_cli",)


def report_cli(installed_cli, material, directory, track=None):
    declaration = material[-1]()
    if track is not None:
        value = json.loads(declaration.read_text(encoding="utf-8"))
        value["track_refs"]["tradeoffs"] = save(material[0], "tradeoffs-input.json", track)
        save(material[0], "research.json", value)
    result = installed_cli(
        "research", "report", declaration, "--track", "tradeoffs", "--directory", directory
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((directory / "tradeoffs.json").read_text(encoding="utf-8"))


def test_absent_resource_material_keeps_all_planned_slots(
    installed_cli, research_material, tmp_path
):
    report = report_cli(installed_cli, research_material, tmp_path / "out")
    assert report["population_completion"]["summary"]["planned_completion"]["denominator"] == 80
    assert report["all_attempts"]["planned_slots"] == 80
    assert report["all_attempts"]["missing_usage_attempts"] == 0
    assert report["all_attempts"]["ledger_complete"] is False
    assert report["paired_comparisons"][0]["eligible"] == 20
    assert report["paired_comparisons"][0]["completed"] == 0
    assert report["paired_comparisons"][0]["excluded"] == 20


def usage_attempt(material, version, status="completed", *, order=1, tokens=100, elapsed=10):
    attempt = add_attempt(material, 0, version, status, order=order)
    attempt["group_id"] = "g"
    usage = {
        "schema_version": "rtpeval_usage_1",
        "namespace": "planner",
        "group_id": "g",
        "version": version,
        "run_id": attempt["run_id"],
        "result_sha256": None,
        "outcome": status,
        "collection_status": "available",
        "coverage": {"adapter_coverage": "default_adapters"},
        "timing": {
            "scope": "selected_invocation_through_cleanup",
            "elapsed_seconds": elapsed,
            "started_at": "2026-10-02T00:00:00Z",
        },
        "model_calls": [
            {
                "event_id": "m",
                "provider": "fixture",
                "operation": "chat",
                "model": "test",
                "outcome": "completed",
                "input_tokens": tokens - 20,
                "output_tokens": 20,
                "total_tokens": tokens,
                "cached_input_tokens": 0,
            }
        ],
        "provider_events": [
            {
                "event_id": "h",
                "provider": "fixture",
                "operation": "model_http",
                "outcome": "completed",
                "model_event_id": "m",
                "model_provider": "fixture",
            }
        ],
        "cache_events": [],
        "repair_summary": {"model_event_ids": ["m"], "provider_event_ids": ["h"]},
    }
    attempt["usage_ref"] = save(material[0], attempt["attempt_id"] + "-usage.json", usage)
    return attempt, usage


def test_failure_retry_consumption_is_separate_and_pending_cannot_be_zero(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    usage_attempt(research_material, "v1", "failed", tokens=100, elapsed=3)
    usage_attempt(research_material, "v1", order=2, tokens=200, elapsed=12)
    usage_attempt(research_material, "v2", tokens=300, elapsed=15)
    report = report_cli(installed_cli, research_material, tmp_path / "attempts")
    ledger = report["all_attempts"]
    assert ledger["dispatched_attempts"] == 3
    assert ledger["ledger_complete"] is False
    assert ledger["totals"]["total_tokens"] == {
        "total": None,
        "observed_subtotal": 600,
        "known_attempts": 3,
        "missing_attempts": 0,
    }
    assert ledger["totals"]["model_calls"]["observed_subtotal"] == 3
    assert ledger["totals"]["http_sends"]["observed_subtotal"] == 3
    assert ledger["rows"][0]["selected_primary"] is True
    assert ledger["rows"][1]["selected_primary"] is False
    assert ledger["rows"][0]["elapsed_cohort"] == "failed_or_censored"
    assert ledger["rows"][1]["repair"]["total_tokens"] == 200
    assert report["paired_comparisons"][0]["completed"] == 0
    assert report["population_completion"]["summary"]["planned_completion"]["upper_bound"] == 0.75


def test_partial_token_coverage_and_embedding_output_are_not_fabricated(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v2")
    del usage["model_calls"][0]["output_tokens"]
    del usage["model_calls"][0]["total_tokens"]
    usage["model_calls"].append(
        {
            "event_id": "embed",
            "provider": "fixture",
            "operation": "embedding",
            "model": "embed-test",
            "outcome": "completed",
            "input_tokens": 50,
            "total_tokens": 50,
        }
    )
    usage["provider_events"].append(
        {
            "event_id": "sdk",
            "provider": "fixture",
            "operation": "official_search",
            "source": "sdk_output_tool_calls",
            "outcome": "completed",
            "tool_calls": 1,
        }
    )
    usage["collection_status"] = "partial"
    attempt["usage_ref"] = save(research_material[0], attempt["attempt_id"] + "-usage.json", usage)
    report = report_cli(installed_cli, research_material, tmp_path / "partial")
    row = report["all_attempts"]["rows"][0]
    assert row["metrics"]["input_tokens"] == 130
    assert row["metrics"]["output_tokens"] is None
    assert row["metrics"]["total_tokens"] is None
    assert row["metrics"]["embedding_total_tokens"] == 50
    assert row["observed_subtotals"]["total_tokens"] == 50
    assert row["metrics"]["http_sends"] == 1
    assert row["metrics"]["model_calls"] == 2
    assert (
        report["all_attempts"]["by_version"]["v2"]["totals"]["total_tokens"]["observed_subtotal"]
        == 50
    )
    assert report["all_attempts"]["elapsed_cohorts"][0]["median"] == 10


def cost_track(material, attempts, *, currency="USD", bills=None, basis="fixture-retail"):
    from backend.tests.evaluation.test_cost_report import prices

    catalog = prices()
    catalog["currency"] = currency
    ledger = {
        "attempt_ids": [a["attempt_id"] for a in attempts],
        "prices_ref": save(material[0], "prices-" + currency + ".json", catalog),
        "accounting_basis": basis,
    }
    if bills is not None:
        ledger["bills_ref"] = save(material[0], "bills.json", {"bills": bills})
    return {
        "schema_version": "rtpeval_research_tradeoffs_1",
        "quality_reports": [],
        "cost_ledgers": [ledger],
    }


def test_native_cost_totals_and_repair_subset_are_rebuilt_from_exact_usage(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    research_material[1]["cases"][0]["repetition_ids"] = ["rep-1", "pending-repeat"]
    attempt, _ = usage_attempt(research_material, "v3", tokens=100)
    track = cost_track(research_material, [attempt])
    report = report_cli(installed_cli, research_material, tmp_path / "cost", track)
    cost = report["all_attempts"]["rows"][0]["cost"]
    assert cost["native"]["estimated_total"] == "0.00024"
    assert cost["native"]["best_available_total"] == "0.00024"
    assert cost["native"]["actual_total"] is None
    assert cost["native"]["repair"]["estimated_total"] == "0.00024"
    assert cost["native"]["events"][1]["status"] == "transport_only"
    assert report["all_attempts"]["cost_consumption"][0]["best_available_total"] is None
    assert (
        report["all_attempts"]["cost_consumption"][0]["best_available_observed_subtotal"]
        == "0.00024"
    )


def test_selected_successful_pairs_have_literal_deltas_and_zero_baseline_ratios(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    first, _ = usage_attempt(research_material, "v1", tokens=100, elapsed=0)
    second, _ = usage_attempt(research_material, "v2", tokens=150, elapsed=12)
    track = cost_track(research_material, [first, second])
    report = report_cli(installed_cli, research_material, tmp_path / "paired", track)
    pair = report["paired_comparisons"][0]
    assert (pair["eligible"], pair["completed"], pair["excluded"]) == (1, 1, 0)
    row = pair["rows"][0]
    assert row["resources"]["total_tokens"]["difference"] == 50
    assert row["resources"]["total_tokens"]["ratio"] == 1.5
    assert row["resources"]["elapsed_seconds"] == {
        "difference": 12,
        "ratio": None,
        "reason": "zero_baseline",
    }
    assert row["costs"]["estimated"]["difference"] == "0.0001"
    assert row["costs"]["estimated"]["reason"] is None
    assert row["quality"]["availability"] == "missing_native_quality"
    assert pair["descriptive_medians"]["total_tokens"]["difference"] == 50
    assert pair["completion_difference"]["difference"] == 0.0
    assert report["population_completion"]["summary"]["planned_completion"]["denominator"] == 4
    assert len(report["paired_comparisons"][1]["rows"]) == 1


def test_incompatible_accounting_and_timing_disable_only_affected_deltas(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    first, _ = usage_attempt(research_material, "v1")
    second, usage = usage_attempt(research_material, "v2", tokens=150)
    usage["timing"]["scope"] = "provider_only"
    second["usage_ref"] = save(research_material[0], second["attempt_id"] + "-usage.json", usage)
    first_ledger = cost_track(research_material, [first])["cost_ledgers"][0]
    second_ledger = cost_track(research_material, [second], basis="different-accounting")[
        "cost_ledgers"
    ][0]
    track = {
        "schema_version": "rtpeval_research_tradeoffs_1",
        "quality_reports": [],
        "cost_ledgers": [first_ledger, second_ledger],
    }
    report = report_cli(installed_cli, research_material, tmp_path / "mismatch", track)
    row = report["paired_comparisons"][0]["rows"][0]
    assert row["resources"]["elapsed_seconds"]["difference"] is None
    assert row["resources"]["total_tokens"]["difference"] == 50
    assert row["costs"]["estimated"]["reason"] == "accounting_basis_mismatch"
    assert row["costs"]["estimated"]["difference"] is None
    assert any(c["field"] == "timing_scope" for c in row["caveats"])


def test_run_bill_and_estimate_basis_do_not_become_a_best_available_delta(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    research_material[1]["cases"][0]["repetition_ids"] = ["rep-1", "missing"]
    first, _ = usage_attempt(research_material, "v1")
    second, _ = usage_attempt(research_material, "v2", tokens=150)
    bill = {
        "bill_id": "run",
        "scope": "run",
        "usage_sha256": first["usage_ref"]["sha256"],
        "result_sha256": None,
        "currency": "USD",
        "amount": "0.1",
        "source": "fixture.csv:1",
        "complete": True,
    }
    track = cost_track(research_material, [first, second], bills=[bill])
    report = report_cli(installed_cli, research_material, tmp_path / "billed", track)
    pair = report["paired_comparisons"][0]["rows"][0]
    assert pair["costs"]["estimated"]["difference"] == "0.0001"
    assert pair["costs"]["best_available"]["difference"] is None
    assert pair["costs"]["best_available"]["reason"] == "billing_basis_mismatch"
    consumed = report["all_attempts"]["cost_consumption"][0]
    assert consumed["actual_total"] is None
    assert consumed["actual_known_run_total_subtotal"] == "0.1"
    assert report["all_attempts"]["rows"][0]["cost"]["native"]["repair"]["actual_total"] is None


@pytest.mark.parametrize(
    "corruption",
    ["namespace", "usage_hash", "outcome", "frozen", "cost_attempt", "bill_hash", "forged_cost"],
)
def test_foreign_or_contradictory_resource_material_is_rejected(
    installed_cli, research_material, tmp_path, corruption
):
    from backend.evaluation.cost_report import build_cost_report
    from backend.tests.evaluation.test_cost_report import prices

    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v1")
    track = cost_track(research_material, [attempt])
    if corruption == "namespace":
        usage["namespace"] = "oracle"
    elif corruption == "outcome":
        usage["outcome"] = "failed"
    elif corruption == "frozen":
        usage["usage_scope"] = "frozen_simulation"
    if corruption in ("namespace", "outcome", "frozen"):
        attempt["usage_ref"] = save(
            research_material[0], attempt["attempt_id"] + "-usage.json", usage
        )
    elif corruption == "usage_hash":
        attempt["usage_ref"]["sha256"] = "f" * 64
    elif corruption == "cost_attempt":
        track["cost_ledgers"][0]["attempt_ids"] = ["foreign"]
    elif corruption == "bill_hash":
        track["cost_ledgers"][0]["bills_ref"] = save(
            research_material[0],
            "foreign-bill.json",
            {
                "bills": [
                    {
                        "bill_id": "b",
                        "scope": "run",
                        "usage_sha256": "f" * 64,
                        "result_sha256": None,
                        "currency": "USD",
                        "amount": "1",
                        "source": "fake.csv:1",
                        "complete": True,
                    }
                ]
            },
        )
    elif corruption == "forged_cost":
        cost = build_cost_report(
            [{"sha256": attempt["usage_ref"]["sha256"], "usage": usage}], prices()
        )
        cost["runs"][0]["estimated_total"] = "9"
        track["cost_ledgers"][0]["report_ref"] = save(research_material[0], "fake-cost.json", cost)
    declaration = research_material[-1]()
    value = json.loads(declaration.read_text(encoding="utf-8"))
    value["track_refs"]["tradeoffs"] = save(research_material[0], "tradeoffs-input.json", track)
    save(research_material[0], "research.json", value)
    result = installed_cli("research", "validate", declaration, "--track", "tradeoffs")
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


def test_reproducible_report_has_coverage_profiles_and_readable_comparisons(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    usage_attempt(research_material, "v1", tokens=100)
    usage_attempt(research_material, "v2", tokens=150)
    first = report_cli(installed_cli, research_material, tmp_path / "fresh-one")
    second = report_cli(installed_cli, research_material, tmp_path / "fresh-two")
    assert first == second
    assert first["profile_ids"] == {"selection": "fixed-selection", "selection_revision": "p1"}
    assert first["measurement_coverage"]["dispatched_attempts"] == 2
    assert first["review_coverage"]["native_quality_groups"] == 0
    assert first["population_digest"] == first["population_completion"]["population_digest"]
    markdown = (tmp_path / "fresh-one" / "tradeoffs.md").read_text(encoding="utf-8")
    assert "v2 minus v1" in markdown
    assert "50" in markdown
    assert "failed/censored" in markdown
    assert "2/4" in markdown
    repeated = installed_cli(
        "research",
        "report",
        research_material[-1](),
        "--track",
        "tradeoffs",
        "--directory",
        tmp_path / "fresh-one",
    )
    assert repeated.returncode == 2
