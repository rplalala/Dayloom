"""Offline installed generation tradeoff acceptance."""

import json

import pytest

from backend.tests.evaluation import test_v3_pair_report as native_pairs
from backend.tests.research_native_fixtures import (
    declare_native,
    final_case,
    native_descriptor,
    prepare_namespaced_usage,
)
from backend.tests.test_rtpeval_research_population_cli import add_attempt, save

pair_case = native_pairs.pair_case
route_case = native_pairs.route_case
prepared_scenario = native_pairs.prepared_scenario

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


def native_usage(batch):
    prepare_namespaced_usage(batch)
    manifest, _, write, saver, root = batch
    for version, run in manifest["groups"][0]["selected_runs"].items():
        usage = json.loads((root / run["usage_ref"]["path"]).read_bytes())
        tokens = 150 if version == "v2" else 100
        usage.update(
            namespace="planner",
            outcome="completed",
            collection_status="available",
            coverage={"adapter_coverage": "default_adapters"},
            timing={
                "scope": "selected_invocation_through_cleanup",
                "elapsed_seconds": 10,
                "started_at": "2026-10-02T00:00:00Z",
            },
            model_calls=[
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
            provider_events=[],
            cache_events=[],
        )
        run["usage_ref"] = saver(run["usage_ref"]["path"], usage, usage["schema_version"])
    write()


def native_declaration(batch, pair_case):
    root = batch[-1]
    native_usage(batch)
    quality = native_descriptor(root, final_case(pair_case()), "quality")
    declaration = declare_native(root, batch[0], quality=[quality])
    value = json.loads(declaration.read_bytes())
    value["track_refs"]["tradeoffs"] = save(
        root,
        "tradeoffs-input.json",
        {
            "schema_version": "rtpeval_research_tradeoffs_1",
            "quality_reports": [quality],
            "cost_ledgers": [],
        },
    )
    save(root, "research.json", value)
    return declaration, quality


def test_real_native_quality_is_linked_with_selected_resource_pair(
    installed_cli, batch, pair_case, tmp_path
):
    declaration, descriptor = native_declaration(batch, pair_case)
    source = json.loads((batch[-1] / descriptor["report_ref"]["path"]).read_bytes())
    result = installed_cli(
        "research",
        "report",
        declaration,
        "--track",
        "tradeoffs",
        "--directory",
        tmp_path / "native",
        evaluation_offline=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "native" / "tradeoffs.json").read_bytes())
    pair = report["paired_comparisons"][0]
    assert pair["native_quality_pairs"] == 1
    row = pair["rows"][0]
    assert row["resources"]["total_tokens"]["difference"] == 50
    assert row["quality"]["totals"]["auxiliary_total"]["difference"] == 0.0
    assert row["quality"]["totals"]["auxiliary_total"]["exact_fraction"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert row["quality"]["included_dimensions"] == [
        "grounding",
        "non_overlap",
        "opening",
        "routes",
    ]
    assert row["quality"]["baseline_native"] == source["groups"][0]["versions"]["v1"]
    assert row["quality"]["candidate_native"] == source["groups"][0]["versions"]["v2"]
    assert (
        report["paired_comparisons"][1]["rows"][0]["quality"]["totals"]["overall_total"][
            "difference"
        ]
        == 0.0
    )
    assert pair["quality_medians"]["auxiliary_total"]["difference"] == 0.0


@pytest.mark.parametrize("fault", ["quality", "usage", "provenance"])
def test_native_quality_join_rejects_freshly_hashed_foreign_material(
    installed_cli, batch, pair_case, tmp_path, fault
):
    from backend.evaluation.quality_report import quality_content_hash

    declaration, descriptor = native_declaration(batch, pair_case)
    root = batch[-1]
    declared = json.loads(declaration.read_bytes())
    if fault == "quality":
        quality = json.loads((root / descriptor["report_ref"]["path"]).read_bytes())
        quality["groups"][0]["versions"]["v2"]["auxiliary_total"]["score_0_100"] = 99
        quality["content_hash"] = quality_content_hash(quality)
        descriptor["report_ref"] = save(root, "forged-quality.json", quality)
        declared["track_refs"]["tradeoffs"] = save(
            root,
            "tradeoffs-input.json",
            {
                "schema_version": "rtpeval_research_tradeoffs_1",
                "quality_reports": [descriptor],
                "cost_ledgers": [],
            },
        )
    else:
        census = json.loads((root / declared["census_ref"]["path"]).read_bytes())
        attempt = next(a for a in census["attempts"] if a["version"] == "v2")
        ref = attempt[fault + "_ref"]
        material = json.loads((root / ref["path"]).read_bytes())
        if fault == "usage":
            material["model_calls"][0]["total_tokens"] = 999
        else:
            material["unrelated_note"] = "Different producer capture bytes"
        attempt[fault + "_ref"] = save(root, "foreign-" + fault + ".json", material)
        declared["census_ref"] = save(root, "census.json", census)
    save(root, "research.json", declared)
    result = installed_cli(
        "research", "validate", declaration, "--track", "tradeoffs", evaluation_offline=True
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


def test_unverified_adapter_coverage_prevents_complete_ledger_totals(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    research_material[1]["cases"][0]["planned_versions"] = ["v1"]
    attempt, usage = usage_attempt(research_material, "v1")
    usage["coverage"] = {"adapter_coverage": "unknown"}
    attempt["usage_ref"] = save(research_material[0], attempt["attempt_id"] + "-usage.json", usage)
    report = report_cli(installed_cli, research_material, tmp_path / "unverified")
    ledger = report["all_attempts"]
    assert ledger["ledger_complete"] is False
    assert ledger["by_version"]["v1"]["ledger_complete"] is False
    assert ledger["totals"]["model_calls"]["total"] is None
    assert ledger["totals"]["total_tokens"]["observed_subtotal"] == 100


def test_partial_prices_and_currency_mismatch_retain_native_unavailability(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    left, _ = usage_attempt(research_material, "v1")
    right, _ = usage_attempt(research_material, "v2", tokens=150)
    left_ledger = cost_track(research_material, [left])["cost_ledgers"][0]
    right_ledger = cost_track(research_material, [right], currency="EUR")["cost_ledgers"][0]
    prices = json.loads((research_material[0] / right_ledger["prices_ref"]["path"]).read_bytes())
    prices["rows"] = []
    right_ledger["prices_ref"] = save(research_material[0], "partial-prices.json", prices)
    track = {
        "schema_version": "rtpeval_research_tradeoffs_1",
        "quality_reports": [],
        "cost_ledgers": [left_ledger, right_ledger],
        "comparisons": [
            {"baseline": "v0", "candidate": "v2"},
            {"baseline": "v1", "candidate": "v2"},
        ],
    }
    report = report_cli(installed_cli, research_material, tmp_path / "partial-cost", track)
    assert len(report["paired_comparisons"]) == 2
    pair = report["paired_comparisons"][1]["rows"][0]
    assert pair["costs"]["estimated"]["reason"] == "currency_mismatch"
    native = report["all_attempts"]["rows"][1]["cost"]["native"]
    assert native["estimated_total"] is None
    assert native["unpriced_event_count"] == 1
    assert native["events"][0]["missing_reason"] == "missing_price_or_billing_context"


def test_capture_completed_but_workflow_failed_stays_in_failed_consumption(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v2", "required_mechanism_failed")
    usage["outcome"] = "completed"
    attempt["usage_ref"] = save(research_material[0], attempt["attempt_id"] + "-usage.json", usage)
    report = report_cli(installed_cli, research_material, tmp_path / "mechanism-failed")
    row = report["all_attempts"]["rows"][0]
    assert row["status"] == "failed"
    assert row["native_usage"]["outcome"] == "completed"
    assert row["elapsed_cohort"] == "failed_or_censored"
    assert report["all_attempts"]["totals"]["total_tokens"]["observed_subtotal"] == 100
    assert report["paired_comparisons"][0]["completed"] == 0


@pytest.mark.parametrize("field", ["coverage", "timing", "repair_summary"])
def test_malformed_usage_objects_are_material_errors(installed_cli, research_material, field):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v1")
    usage[field] = []
    attempt["usage_ref"] = save(research_material[0], attempt["attempt_id"] + "-usage.json", usage)
    result = installed_cli("research", "validate", research_material[-1](), "--track", "tradeoffs")
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


def test_zero_cost_baseline_retains_difference_without_ratio_and_cost_median(
    installed_cli, research_material, tmp_path
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    left, usage = usage_attempt(research_material, "v1")
    usage.update(
        model_calls=[],
        provider_events=[],
        repair_summary={"model_event_ids": [], "provider_event_ids": []},
    )
    left["usage_ref"] = save(research_material[0], left["attempt_id"] + "-usage.json", usage)
    right, _ = usage_attempt(research_material, "v2")
    report = report_cli(
        installed_cli,
        research_material,
        tmp_path / "zero-cost",
        cost_track(research_material, [left, right]),
    )
    pair = report["paired_comparisons"][0]
    cost = pair["rows"][0]["costs"]["best_available"]
    assert cost == {"difference": "0.00024", "ratio": None, "reason": "zero_baseline"}
    assert pair["cost_medians"][0]["mode"] == "best_available"
    assert pair["cost_medians"][0]["difference"] == "0.00024"
    assert pair["cost_medians"][0]["currency"] == "USD"


@pytest.mark.parametrize(
    "field", ["bills", "annotations", "price_rows", "price_match", "price_rates"]
)
def test_malformed_accounting_objects_are_material_errors(installed_cli, research_material, field):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, _ = usage_attempt(research_material, "v1")
    track = cost_track(research_material, [attempt])
    ledger = track["cost_ledgers"][0]
    if field in ("bills", "annotations"):
        ledger[field + "_ref"] = save(
            research_material[0], field + ".json", {field: {"invalid": "object instead of array"}}
        )
    else:
        prices = json.loads((research_material[0] / ledger["prices_ref"]["path"]).read_bytes())
        if field == "price_rows":
            prices["rows"] = {"invalid": "object instead of array"}
        elif field == "price_match":
            prices["rows"][0]["match"] = []
        else:
            prices["rows"][0]["rates"] = ["input_tokens"]
        ledger["prices_ref"] = save(research_material[0], "malformed-prices.json", prices)
    declaration = research_material[-1]()
    declared = json.loads(declaration.read_bytes())
    declared["track_refs"]["tradeoffs"] = save(research_material[0], "tradeoffs-input.json", track)
    save(research_material[0], "research.json", declared)
    result = installed_cli("research", "validate", declaration, "--track", "tradeoffs")
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"


@pytest.mark.parametrize(
    "fault",
    ["fields_list", "billing_context_list", "billing_context_none", "observed_context_list"],
)
def test_annotation_nested_objects_are_material_errors(installed_cli, research_material, fault):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v1")
    if fault == "observed_context_list":
        usage["model_calls"][0]["billing_context"] = []
        attempt["usage_ref"] = save(research_material[0], "bad-context-usage.json", usage)
    fields = {"billing_context": {"region": "fixture"}}
    if fault == "fields_list":
        fields = ["cached_input_tokens"]
    elif fault == "billing_context_list":
        fields["billing_context"] = ["region"]
    elif fault == "billing_context_none":
        fields["billing_context"] = None
    track = cost_track(research_material, [attempt])
    track["cost_ledgers"][0]["annotations_ref"] = save(
        research_material[0],
        "annotations.json",
        {
            "annotations": [
                {
                    "usage_sha256": attempt["usage_ref"]["sha256"],
                    "kind": "model",
                    "event_id": "m",
                    "source": "independent-ledger",
                    "note": "Reviewed billing detail",
                    "source_sha256": "a" * 64,
                    "fields": fields,
                }
            ],
        },
    )
    declaration = research_material[-1]()
    value = json.loads(declaration.read_bytes())
    value["track_refs"]["tradeoffs"] = save(research_material[0], "tradeoffs-input.json", track)
    save(research_material[0], declaration.name, value)
    result = installed_cli("research", "validate", declaration, "--track", "tradeoffs")
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(result.stdout)["processing_status"] == "needs_material_correction"
    assert "Malformed native" in result.stdout


@pytest.mark.parametrize("context", [False, True])
def test_valid_annotation_objects_retain_native_cost_and_original_usage(
    installed_cli, research_material, tmp_path, context
):
    research_material[1]["cases"] = research_material[1]["cases"][:1]
    attempt, usage = usage_attempt(research_material, "v1")
    usage["model_calls"][0].pop("cached_input_tokens")
    attempt["usage_ref"] = save(research_material[0], "annotated-original-usage.json", usage)
    original = (research_material[0] / attempt["usage_ref"]["path"]).read_bytes()
    fields = {"cached_input_tokens": 0}
    if context:
        fields["billing_context"] = {"region": "fixture"}
    track = cost_track(research_material, [attempt])
    track["cost_ledgers"][0]["annotations_ref"] = save(
        research_material[0],
        "annotations.json",
        {
            "annotations": [
                {
                    "usage_sha256": attempt["usage_ref"]["sha256"],
                    "kind": "model",
                    "event_id": "m",
                    "source": "independent-ledger",
                    "note": "Reviewed billing detail",
                    "source_sha256": "a" * 64,
                    "fields": fields,
                }
            ],
        },
    )
    value = report_cli(installed_cli, research_material, tmp_path / "valid", track)
    native = value["all_attempts"]["rows"][0]["cost"]["native"]
    assert native["estimated_total"] == "0.00024"
    assert native["actual_total"] is None
    assert (research_material[0] / attempt["usage_ref"]["path"]).read_bytes() == original
