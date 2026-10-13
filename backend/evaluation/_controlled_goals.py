"""Reviewed controlled conditions linked to independent paired checks."""

from datetime import date as Date
from typing import Literal

from pydantic import Field, model_validator

from .controlled_models import FrozenModel
from .place_association import opening_place_id
from .records import require
from .repair_selection import selected_prefix


class Condition(FrozenModel):
    kind: Literal["check", "daily_count", "repeat_count"]
    dimension: (
        Literal[
            "requirements", "grounding", "opening", "routes", "conflicts", "protection_conflicts"
        ]
        | None
    ) = None
    activity_ids: tuple[str, ...] = ()
    obligation_id: str | None = None
    canonical_place_id: str | None = None
    date: Date | None = None
    minimum: int | None = Field(default=None, ge=0)
    maximum: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def applicable(self):
        if self.kind == "check":
            if self.dimension is None or not (self.activity_ids or self.obligation_id):
                raise ValueError("Check conditions require a dimension and exact subject selector")
            if self.minimum is not None or self.maximum is not None:
                raise ValueError("Check conditions do not use count limits")
        else:
            if self.dimension is not None or self.activity_ids or self.obligation_id:
                raise ValueError("Count conditions use a date or canonical venue selector")
            if (self.kind == "daily_count" and self.date is None) or (
                self.kind == "repeat_count" and self.canonical_place_id is None
            ):
                raise ValueError("Count condition subject required")
            if (self.kind == "daily_count" and self.canonical_place_id is not None) or (
                self.kind == "repeat_count" and self.date is not None
            ):
                raise ValueError("Use daily count by date or repetition count over the whole trip")
            if self.minimum is None and self.maximum is None:
                raise ValueError("Count conditions require a declared limit")
            if (
                self.minimum is not None
                and self.maximum is not None
                and self.minimum > self.maximum
            ):
                raise ValueError("Inverted count limits")
        return self


class Detector(FrozenModel):
    check: str = Field(min_length=1)
    reason: str | None = None
    activity_ids: tuple[str, ...] = ()
    place_ids: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()
    dates: tuple[Date, ...] = ()


class Goal(FrozenModel):
    goal_id: str = Field(min_length=1)
    basis: Literal[
        "confirmed_conflict", "explicit_requirement", "product_policy", "review_opportunity"
    ]
    condition: Condition
    detector: Detector | None = None
    source: dict | None = None


class Expectations(FrozenModel):
    schema_version: Literal["rtpeval_controlled_expectations_1"]
    case_id: str
    case_hash: str
    revision: str = Field(min_length=1)
    reviewer_ref: str = Field(min_length=1)
    reviewed_at: str
    rationale: str = Field(min_length=1)
    supporting_refs: tuple[str, ...] = Field(min_length=1)
    targets: tuple[Goal, ...]
    guards: tuple[Goal, ...]

    @model_validator(mode="after")
    def inventory(self):
        ids = [g.goal_id for g in (*self.targets, *self.guards)]
        if len(ids) != len(set(ids)):
            raise ValueError("Controlled goal IDs must be unique")
        if any(g.detector is None for g in self.targets):
            raise ValueError("Every expected target requires a detector specification")
        return self


def subject_ids(check, stage):
    """Map evaluator references to original occurrence IDs, never infer title semantics."""
    refs = {
        r["source"]["record_id"]: r["original"].get("activity_id")
        for r in stage["controlled_projection"]["activities"]
    }
    source_ids = set()
    for field in ("source", "from_source", "to_source"):
        if isinstance(check.get(field), dict):
            source_ids.add(check[field].get("record_id"))
    commitments = set(check.get("commitment_ids", []))
    if check.get("commitment_id"):
        commitments.add(check["commitment_id"])
    for unit in stage["occupancy"]["commitments"]:
        if unit["commitment_id"] in commitments:
            source_ids.update(s["record_id"] for s in unit["sources"])
    return {refs[s] for s in source_ids if s in refs}


def matches(check, condition, stage):
    return (
        (not condition.activity_ids or set(condition.activity_ids) <= subject_ids(check, stage))
        and (
            condition.obligation_id is None or check.get("obligation_id") == condition.obligation_id
        )
        and (
            condition.canonical_place_id is None
            or (
                opening_place_id(check)
                if condition.dimension == "opening"
                else check.get("canonical_place_id")
            )
            == condition.canonical_place_id
        )
        and (condition.date is None or check.get("declared_day") == str(condition.date))
    )


def checks(stage, dimension):
    if dimension in {"conflicts", "protection_conflicts"}:
        return stage["schedule_measures"][
            "commitment_pairs" if dimension == "conflicts" else "protection_conflicts"
        ]
    return stage["primary_metrics"][dimension]["checks"]


def verdict(stage, condition):
    if condition.kind == "check":
        selected = [c for c in checks(stage, condition.dimension) if matches(c, condition, stage)]
        # Conflict lists contain only conflicts; absence needs complete subject occupancy.
        if not selected and condition.dimension in {"conflicts", "protection_conflicts"}:
            if condition.dimension == "protection_conflicts" and not condition.activity_ids:
                # The independent obligation check already assesses every applicable
                # commitment and unresolved candidate under the protection's scope.
                protected = [
                    c
                    for c in checks(stage, "requirements")
                    if c["kind"] == "protected_time"
                    and c["obligation_id"] == condition.obligation_id
                ]
                has_blocker = any(
                    condition.obligation_id in b["obligation_ids"]
                    for b in stage["occupancy"]["blockers"]
                )
                state = protected[0]["state"] if has_blocker and len(protected) == 1 else "UNKNOWN"
                return {"state": state, "checks": []}
            units = [
                u
                for u in stage["occupancy"]["commitments"]
                if set(condition.activity_ids)
                & subject_ids({"commitment_id": u["commitment_id"]}, stage)
            ]
            present = set().union(
                *(subject_ids({"commitment_id": u["commitment_id"]}, stage) for u in units)
            )
            clear = (
                bool(units)
                and set(condition.activity_ids) <= present
                and all(u["time_complete"] for u in units)
            )
            if condition.dimension == "protection_conflicts":
                clear &= any(
                    condition.obligation_id in b["obligation_ids"]
                    for b in stage["occupancy"]["blockers"]
                )
            return {"state": "PASS" if clear else "UNKNOWN", "checks": []}
        state = (
            "FAIL"
            if any(c["state"] == "FAIL" for c in selected)
            else (
                "UNKNOWN"
                if not selected or any(c["state"] == "UNKNOWN" for c in selected)
                else "PASS"
            )
        )
        return {"state": state, "checks": selected}
    descriptive = stage["descriptive"]
    if condition.kind == "daily_count":
        row = next((r for r in descriptive["density"] if r["date"] == str(condition.date)), None)
        if row is None:
            return {"state": "UNKNOWN", "reason": "missing_declared_day"}
        lower = row["known_primary_count"]
        upper = lower + row["possible_primary_count"]
    else:
        rows = descriptive["repetition"]["venues"]
        row = next(
            (r for r in rows if r["canonical_place_id"] == condition.canonical_place_id), None
        )
        lower = row["occurrence_count"] if row else 0
        upper = lower + descriptive["repetition"]["unknown_identity_occurrences"]
    failed = (condition.minimum is not None and upper < condition.minimum) or (
        condition.maximum is not None and lower > condition.maximum
    )
    passed = (condition.minimum is None or lower >= condition.minimum) and (
        condition.maximum is None or upper <= condition.maximum
    )
    return {
        "state": "FAIL" if failed else "PASS" if passed else "UNKNOWN",
        "known_count": lower,
        "possible_count": upper,
    }


def detection(goal, outcome):
    detector = goal.detector
    expected = "NEEDS_REVIEW" if goal.basis == "review_opportunity" else "CONFIRMED"
    found = []
    for finding in outcome["original_report"]["findings"]:
        if finding["check"] != detector.check or finding["status"] != expected:
            continue
        if detector.reason is not None and finding["reason"] != detector.reason:
            continue
        if all(
            not getattr(detector, field)
            or set(map(str, getattr(detector, field))) <= set(finding[field])
            for field in ("activity_ids", "place_ids", "requirement_ids", "dates")
        ):
            found.append(finding["finding_id"])
    scope = outcome["scope"]
    authorized = set(found) & set(scope["target_ids"] if scope else [])
    repair = outcome["repair"]
    opportunities, components, attempted = [], [], False
    prefix = selected_prefix(repair) if repair else None
    transitions = promotions = 0
    deterministic_attempted = False
    if repair and authorized:
        rounds = repair["rounds"]
        if not rounds and prefix is None:
            rounds = [{"round_index": 0, "result": repair, "target_links": {}}]
        previous_deterministic = 0
        for round_ in rounds:
            result, links = round_["result"], round_["target_links"]
            local = {
                tid
                for tid in (result.get("scope") or {}).get("target_ids", [])
                if links.get(tid, tid) in authorized
            }
            deterministic_count = result.get("counters", {}).get("deterministic_attempts", 0)
            deterministic_sent = deterministic_count > previous_deterministic
            previous_deterministic = deterministic_count
            attempted |= bool(local and result["model_attempted"])
            if prefix is not None and local:
                transitions += round_["exploration_transition"]
                promotions += round_["best_promoted"]
                deterministic_attempted |= (
                    round_["strategy"] == "system_delete" and deterministic_sent
                )
            preparation = result.get("candidate_preparation") or {}
            opportunities.extend(
                {"round_index": round_["round_index"], "kind": "candidate", **r}
                for r in preparation.get("target_opportunities", [])
                if r["target_id"] in local
            )
            finding_subjects = {
                aid
                for f in result["original_report"]["findings"]
                if f["finding_id"] in local
                for aid in f["activity_ids"]
            }
            opportunities.extend(
                {"round_index": round_["round_index"], "kind": "identity_free", **r}
                for r in preparation.get("identity_free_operations", [])
                if r["activity_id"] in finding_subjects
            )
            components.extend(
                {
                    "round_index": round_["round_index"],
                    **(
                        {
                            "selected_lineage": round_["round_index"] <= prefix
                            and round_["exploration_transition"]
                        }
                        if prefix is not None
                        else {}
                    ),
                    **c,
                }
                for c in result.get("components", [])
                if any(kind == "target" and tid in local for kind, tid in c["dependencies"])
            )
    return {
        "detection": "detected" if found else "missed",
        "finding_ids": found,
        "authorization": "authorized" if authorized else "not_authorized",
        "authorized_finding_ids": sorted(authorized),
        "opportunities": opportunities,
        "components": components,
        "model_attempted": attempted,
        **(
            {
                "operation_attempted": attempted or deterministic_attempted,
                "deterministic_attempted": deterministic_attempted,
                "exploration_transitions": transitions,
                "best_promotions": promotions,
            }
            if prefix is not None
            else {}
        ),
        "adoption": "adopted_component"
        if any(
            c["status"] == "accepted" and c.get("selected_lineage") is not False for c in components
        )
        else "not_adopted",
        "repair_status": repair["status"] if repair else "not_executed",
    }


def target_outcome(goal, pair):
    before = verdict(pair["stages"]["draft"], goal.condition)
    after = verdict(pair["stages"]["final_primary"], goal.condition)
    if goal.condition.kind == "check":
        continuity = [
            r
            for r in pair["continuity"][goal.condition.dimension]
            if r.get("before") and matches(r["before"], goal.condition, pair["stages"]["draft"])
        ]
        transitions = [r["transition"] for r in continuity]
        retained = [r["after"] for r in continuity if r.get("after")]
        if retained:
            after = {
                "state": "FAIL"
                if any(c["state"] == "FAIL" for c in retained)
                else "UNKNOWN"
                if any(c["state"] == "UNKNOWN" for c in retained)
                else "PASS",
                "checks": retained,
            }
        if any(
            t in {"removed", "not_comparable", "structural_leg_removed", "removed_participant"}
            for t in transitions
        ):
            result = "structural_change"
        elif not continuity or any(
            t
            in {
                "unresolved_correspondence",
                "structural_change",
                "lost_verification",
                "unverified_change",
            }
            for t in transitions
        ):
            result = "unresolved"
        elif before["state"] == "FAIL" and after["state"] == "PASS" and "resolved" in transitions:
            result = "resolved"
        elif "regression" in transitions or "introduced_conflict" in transitions:
            result = "regressed"
        elif any(t == "partial_observed_improvement" for t in transitions):
            result = "partial_improvement"
        else:
            result = (
                "regressed"
                if after["state"] == "FAIL" and before["state"] == "PASS"
                else (
                    "residual"
                    if after["state"] == "FAIL"
                    else "unresolved"
                    if after["state"] == "UNKNOWN"
                    else "valid_no_change"
                )
            )
    else:
        result = (
            "unresolved"
            if "UNKNOWN" in (before["state"], after["state"])
            else "resolved"
            if before["state"] == "FAIL" and after["state"] == "PASS"
            else "regressed"
            if before["state"] == "PASS" and after["state"] == "FAIL"
            else "residual"
            if after["state"] == "FAIL"
            else "valid_no_change"
        )
        transitions = []
    if goal.basis != "review_opportunity":
        require(
            before["state"] != "PASS", "targets", "Expected violation is independently compliant"
        )
    return {
        "goal_id": goal.goal_id,
        "basis": goal.basis,
        "condition": goal.condition.model_dump(mode="json"),
        "before": before,
        "after": after,
        "transitions": transitions,
        "independent_outcome": result,
    }
