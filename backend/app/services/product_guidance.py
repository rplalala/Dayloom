"""Traveler-facing hard-request attention from retained native obligations."""


def attention_items(result):
    diagnostics = result.generation_diagnostics
    if diagnostics is None:
        return ()
    contract = getattr(result, "interpreted_requirements", None)
    names = (
        {row.requirement_id: row.place_text for row in contract.named_places} if contract else {}
    )
    findings = getattr(getattr(getattr(result, "v3", None), "final_report", None), "findings", ())
    items = []
    seen = set()
    for issue in diagnostics.policy_issues:
        reason, rid = issue["reason"], issue.get("requirement_id")
        if reason in {"required_visit_obligation_unmet", "visit_requirement_unresolved"}:
            key = ("named", rid)
            title = names.get(rid, "A requested place")
            description = (
                "Your requested visits or dates for this place are not fully arranged. "
                "Review your request before planning again."
            )
            pids = {
                pid
                for finding in findings
                if rid in finding.requirement_ids
                for pid in finding.place_ids
            }
            visits = tuple(
                dict(activity_id=a.activity_id, date=day.date, place_name=a.place_name)
                for day in result.itinerary.days
                for a in day.activities
                if a.source_place_id in pids and a.place_name and a.activity_kind == "main_poi"
            )
        elif reason == "daily_visit_count_unmet":
            key = ("day", issue["date"])
            title = f"Visits on {issue['date']}"
            description = (
                "The visits on this day do not yet match your daily request. "
                "Review this day before planning again."
            )
            visits = ()
        else:
            continue
        if key not in seen:
            items.append(dict(title=title, description=description, planned_visits=visits))
            seen.add(key)
    return tuple(items)
