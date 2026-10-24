"""Structural validation and provenance, never natural-language interpretation."""

import hashlib
import json

from pydantic import ValidationError

from backend.app.schemas.interpreted_requirements import (
    CanonicalSubject,
    ClarificationRequired,
    DailyPace,
    DiscoveryIntent,
    ExperienceEvidenceRequest,
    InterpretationDraft,
    InterpretedTripRequirements,
    NamedRequirement,
    RequirementAssessment,
    SemanticRequirement,
    SourceQuote,
    SourceReference,
    TimeProtection,
    TransportConstraint,
    VisitRequirement,
)
from backend.app.schemas.request import PlanningRequest
from backend.app.schemas.requirement_boundary import RequirementBoundaryError


def locate_source(text: str, source: SourceQuote) -> SourceReference:
    start = -1
    for _ in range(source.occurrence + 1):
        start = text.find(source.quote, start + 1)
        if start < 0:
            break
    if start >= 0:
        return SourceReference(**source.model_dump(), start=start, end=start + len(source.quote))
    # An invalid exact occurrence must not silently change matching domains.
    if source.quote in text or source.occurrence != 0:
        raise RequirementBoundaryError("invalid_source_occurrence")
    folded = ""
    boundaries = {0: 0}
    for index, character in enumerate(text):
        folded += character.casefold()
        boundaries[len(folded)] = index + 1
    needle = source.quote.casefold()
    matches = []
    position = folded.find(needle)
    while position >= 0:
        end = position + len(needle)
        if position in boundaries and end in boundaries:
            matches.append((boundaries[position], boundaries[end]))
        position = folded.find(needle, position + 1)
    if len(matches) != 1:
        raise RequirementBoundaryError(
            "ambiguous_casefold_source" if matches else "invalid_source_occurrence"
        )
    start, end = matches[0]
    return SourceReference(
        quote=text[start:end], occurrence=0, start=start, end=end, match_mode="casefold_equivalent"
    )


def _key(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def _sources(refs, text):
    return tuple(
        sorted(
            set(locate_source(text, r) for r in refs),
            key=lambda r: (r.start, r.end, r.quote, r.match_mode),
        )
    )


def _definitions(items):
    keys = [i.local_key for i in items]
    if any(not key.strip() for key in keys) or len(keys) != len(set(keys)):
        raise RequirementBoundaryError("duplicate_or_blank_local_keys")


def validate_canonical_requirements(contract, request: PlanningRequest):
    """Idempotent documented canonical path: validate, never reinterpret or renumber."""
    text = request.additional_preferences
    try:
        value = InterpretedTripRequirements.model_validate(contract.model_dump())
    except ValidationError as exc:
        raise RequirementBoundaryError(
            "invalid_canonical_contract", stage="canonical_domain", errors=_errors(exc)
        ) from exc
    if (
        value.structured_input_sha256 != request.structured_hash()
        or value.requirements != request.trip_requirements()
    ):
        raise RequirementBoundaryError("canonical_structured_input_mismatch")
    if value.interpretation_origin != ("model" if text else "skipped_empty"):
        raise RequirementBoundaryError("canonical_interpretation_origin_mismatch")
    if value.request_sha256 != hashlib.sha256(text.encode()).hexdigest():
        raise RequirementBoundaryError("canonical_request_mismatch")
    for group in (
        value.subjects,
        value.semantic_requirements,
        value.named_places,
        value.time_protections or (),
        value.visit_requirements or (),
        value.daily_pace or (),
        value.daily_visit_constraints or (),
    ):
        for item in group:
            for ref in item.source_refs:
                if (
                    not 0 <= ref.start < ref.end <= len(text)
                    or text[ref.start : ref.end] != ref.quote
                ):
                    raise RequirementBoundaryError("invalid_canonical_source")
    for item in value.named_places:
        if not any(item.place_text in ref.quote for ref in item.source_refs):
            raise RequirementBoundaryError("named_surface_not_in_source")
    for item in value.semantic_requirements:
        focus = item.soft_coverage.focus_source if item.soft_coverage else None
        if focus and (
            text[focus.start : focus.end] != focus.quote
            or locate_source(text, SourceQuote(quote=focus.quote, occurrence=focus.occurrence))
            != focus
            or not any(focus.start < r.end and r.start < focus.end for r in item.source_refs)
        ):
            raise RequirementBoundaryError("invalid_canonical_focus_source")
    for visit in value.visit_requirements or ():
        matches = [
            n
            for n in value.named_places
            if n.requirement_id == visit.requirement_id and n.place_text == visit.place_text
        ]
        if len(matches) != 1 or any(
            not request.start_date <= d <= request.end_date for d in visit.dates
        ):
            raise RequirementBoundaryError("invalid_visit_requirement_scope")
    for protection in value.time_protections or ():
        if any(not request.start_date <= d <= request.end_date for d in protection.dates):
            raise RequirementBoundaryError("time_protection_outside_request")
    pace = value.daily_pace
    if pace is not None:
        if len({p.date for p in pace}) != len(pace) or sum(p.date is None for p in pace) != 1:
            raise RequirementBoundaryError(
                "invalid_daily_pace_scope",
                errors=({"loc": ("daily_pace",), "type": "invalid_daily_pace_scope"},),
            )
        for i, p in enumerate(pace):
            if p.date is not None and not request.start_date <= p.date <= request.end_date:
                raise RequirementBoundaryError(
                    "daily_pace_outside_request",
                    errors=(
                        {"loc": ("daily_pace", i, "date"), "type": "daily_pace_outside_request"},
                    ),
                )
            if not p.source_refs and (
                p.profile != "ordinary" or p.exact_count is not None or p.date is not None
            ):
                raise RequirementBoundaryError(
                    "daily_pace_source_required",
                    errors=(
                        {
                            "loc": ("daily_pace", i, "source_refs"),
                            "type": "daily_pace_source_required",
                        },
                    ),
                )
    _operational_sources(value, text)
    from backend.app.policies.daily_visit_constraints import validate_daily_contract

    validate_daily_contract(value, request)
    restriction = value.transport_constraint
    if restriction is not None:
        semantics = {r.requirement_id: r for r in value.semantic_requirements}
        for ref in restriction.source_refs:
            if (
                text[ref.start : ref.end] != ref.quote
                or locate_source(text, SourceQuote(quote=ref.quote, occurrence=ref.occurrence))
                != ref
            ):
                raise RequirementBoundaryError("invalid_transport_constraint_source")
        linked = [semantics.get(key) for key in restriction.requirement_refs]
        if any(
            r is None
            or r.kind != "constraint"
            or r.scope != "transport"
            or r.strength != "hard"
            or r.subject_refs != ("party",)
            or not set(r.source_refs) <= set(restriction.source_refs)
            for r in linked
        ) or set(restriction.source_refs) != {s for r in linked if r for s in r.source_refs}:
            raise RequirementBoundaryError("invalid_transport_constraint_link")
    return value


def _operational_sources(value, text):
    for info in value.requested_place_information:
        quotes = [info.source_text, info.target_source_text]
        quotes += [q for q in (info.scope_text, info.date_source_text) if q]
        if any(quote not in text for quote in quotes):
            raise RequirementBoundaryError("invalid_information_source")
        if info.target_surface not in info.target_source_text:
            raise RequirementBoundaryError("invalid_information_target")
    if value.transport_preference and value.transport_preference.source_text not in text:
        raise RequirementBoundaryError("invalid_transport_source")


def _errors(exc):
    return tuple({"loc": e["loc"], "type": e["type"]} for e in exc.errors())


def canonicalize_requirements(
    draft: InterpretationDraft, request: PlanningRequest
) -> InterpretedTripRequirements:
    request = PlanningRequest.model_validate(request.model_dump())
    text = request.additional_preferences
    if isinstance(draft, InterpretedTripRequirements):
        return validate_canonical_requirements(draft, request)
    try:
        # Revalidate even fake/model_copy drafts; never trust bypassed validators.
        draft = InterpretationDraft.model_validate(draft.model_dump())
    except ValidationError as exc:
        raise RequirementBoundaryError(
            "invalid_interpretation_draft", stage="draft", errors=_errors(exc)
        ) from exc
    if draft.overflow:
        raise RequirementBoundaryError("extraction_overflow")
    if draft.preference_input_assessment is not None:
        from backend.app.policies.preference_input import check_preference_input

        check_preference_input(draft, request)
    if draft.operational_conflicts:
        conflicts = tuple(
            {
                "field": item.field,
                "source_refs": [r.model_dump() for r in _sources(item.source_refs, text)],
            }
            for item in draft.operational_conflicts
        )
        raise ClarificationRequired("structured_input_conflict", conflicts=conflicts)
    if draft.extraction_issues:
        raise ClarificationRequired("extraction_ambiguity")
    _definitions(draft.subjects)
    _definitions(draft.semantic_requirements)
    subject_rows = []
    for item in draft.subjects:
        refs = _sources(item.source_refs, text)
        subject_rows.append((item, refs))
    subject_rows.sort(
        key=lambda pair: (pair[1][0].start, pair[0].label, _key([s.model_dump() for s in pair[1]]))
    )
    subject_aliases, canonical_subjects, seen_subjects = {}, [], set()
    for item, refs in subject_rows:
        signature = (item.label, refs)
        if signature in seen_subjects:
            raise RequirementBoundaryError("duplicate_subject_definition")
        seen_subjects.add(signature)
        identifier = f"subject_{len(canonical_subjects) + 1}"
        subject_aliases[item.local_key] = identifier
        canonical_subjects.append(
            CanonicalSubject(subject_id=identifier, label=item.label, source_refs=refs)
        )

    rows = []
    for item in draft.semantic_requirements:
        target = item.subject_target
        if target.kind == "unresolved":
            # Validate the grounding before treating attribution as user ambiguity.
            _sources(item.source_refs, text)
            raise ClarificationRequired("unresolved_subject_attribution")
        if target.kind == "party":
            subjects = ("party",)
        else:
            handles = (target.first_ref, *target.additional_refs)
            if not set(handles) <= subject_aliases.keys():
                raise RequirementBoundaryError("unknown_subject_reference")
            subjects = tuple(sorted({subject_aliases[h] for h in handles}))
        fields = item.model_dump(
            exclude={"local_key", "source_refs", "subject_target", "trip_focus_source"}
        )
        fields["subject_refs"] = subjects
        from backend.app.schemas.interpreted_requirements import soft_coverage_eligible

        if soft_coverage_eligible(item):
            fields["soft_coverage"] = {"target": 1, "origin": "ordinary_preference"}
            if item.trip_focus_source:
                focus = locate_source(text, item.trip_focus_source)
                if focus.match_mode != "exact":
                    raise RequirementBoundaryError("trip_focus_source_not_exact")
                if not any(
                    focus.start < r.end and r.start < focus.end
                    for r in _sources(item.source_refs, text)
                ):
                    raise RequirementBoundaryError("trip_focus_source_not_linked")
                fields["soft_coverage"] = {
                    "target": 2,
                    "origin": "current_trip_focus",
                    "focus_source": focus.model_dump(),
                }
        refs = _sources(item.source_refs, text)
        rows.append((item.local_key, fields, refs))
    rows.sort(
        key=lambda row: (row[2][0].start, _key(row[1]), _key([r.model_dump() for r in row[2]]))
    )
    aliases, semantics, exact = {}, [], {}
    for handle, fields, refs in rows:
        signature = _key(fields)
        if signature in exact:
            index = exact[signature]
            old = semantics[index]
            combined = tuple(sorted(set((*old.source_refs, *refs)), key=lambda r: (r.start, r.end)))
            if len(combined) > 3:
                raise RequirementBoundaryError("consolidated_source_overflow")
            semantics[index] = old.model_copy(update={"source_refs": combined})
            aliases[handle] = old.requirement_id
        else:
            identifier = f"semantic_{len(semantics) + 1}"
            aliases[handle] = identifier
            exact[signature] = len(semantics)
            semantics.append(
                SemanticRequirement(requirement_id=identifier, source_refs=refs, **fields)
            )

    named = []
    named_rows = [(n, _sources(n.source_refs, text)) for n in draft.named_places]
    named_rows.sort(
        key=lambda pair: (
            pair[1][0].start,
            pair[0].place_text,
            pair[0].inclusion,
            _key([r.model_dump() for r in pair[1]]),
        )
    )
    for item, refs in named_rows:
        if not any(item.place_text in ref.quote for ref in refs):
            raise RequirementBoundaryError("named_surface_not_in_source")
        named.append(
            NamedRequirement(
                requirement_id=f"named_{len(named) + 1}",
                place_text=item.place_text,
                inclusion=item.inclusion,
                source_refs=refs,
            )
        )
    _operational_sources(draft, text)

    discoveries = {}
    for item in draft.discovery_intents:
        if not set(item.requirement_refs) <= aliases.keys():
            raise RequirementBoundaryError("unknown_discovery_reference")
        key = (item.query_text, item.purpose)
        discoveries.setdefault(key, set()).update(aliases[r] for r in item.requirement_refs)
        if len(discoveries[key]) > 4:
            raise RequirementBoundaryError("discovery_link_overflow")
    discovery = tuple(
        DiscoveryIntent(
            intent_id=f"discovery_{i + 1}",
            query_text=query,
            purpose=purpose,
            requirement_refs=tuple(sorted(refs)),
        )
        for i, ((query, purpose), refs) in enumerate(sorted(discoveries.items()))
    )
    evidence = {}
    for item in draft.experience_evidence_requests:
        identifier = aliases.get(item.requirement_ref)
        if identifier is None:
            raise RequirementBoundaryError("unknown_experience_reference")
        linked = ExperienceEvidenceRequest(
            requirement_id=identifier,
            dimension=item.dimension,
            preferred_values=tuple(sorted(item.preferred_values)),
            avoided_values=tuple(sorted(item.avoided_values)),
        )
        key = (identifier, item.dimension)
        if key in evidence and evidence[key] != linked:
            raise RequirementBoundaryError("conflicting_experience_targets")
        evidence[key] = linked
    try:
        protections = (
            None
            if draft.time_protections is None
            else tuple(
                TimeProtection(
                    **p.model_dump(exclude={"source_refs"}),
                    source_refs=_sources(p.source_refs, text),
                )
                for p in draft.time_protections
            )
        )
        visits = None
        if draft.visit_requirements is not None:
            visits = []
            for v in draft.visit_requirements:
                matches = [n for n in named if n.place_text == v.place_text]
                if len(matches) != 1:
                    raise RequirementBoundaryError("ambiguous_visit_requirement_identity")
                visits.append(
                    VisitRequirement(
                        **v.model_dump(exclude={"source_refs"}),
                        requirement_id=matches[0].requirement_id,
                        source_refs=_sources(v.source_refs, text),
                    )
                )
        if (
            draft.transport_constraint
            and not set(draft.transport_constraint.requirement_refs) <= aliases.keys()
        ):
            raise RequirementBoundaryError("invalid_transport_constraint_link")
        from backend.app.policies.daily_visit_constraints import (
            canonical_daily_constraints,
            derived_pace,
        )

        daily = canonical_daily_constraints(draft, aliases, text, _sources)
        pace = (
            None
            if draft.daily_pace is None
            else tuple(
                DailyPace(
                    **p.model_dump(exclude={"source_refs"}),
                    source_refs=_sources(p.source_refs, text),
                )
                for p in draft.daily_pace
            )
        )
        if daily is not None:
            pace = derived_pace(pace, daily)
        result = InterpretedTripRequirements(
            contract_version="interpreted_requirements_6"
            if daily is not None
            else "interpreted_requirements_5",
            daily_visit_constraints=daily,
            transport_constraint=None
            if draft.transport_constraint is None
            else TransportConstraint(
                allowed_modes=tuple(sorted(draft.transport_constraint.allowed_modes)),
                requirement_refs=tuple(
                    r.requirement_id
                    for r in semantics
                    if r.requirement_id
                    in {aliases[k] for k in draft.transport_constraint.requirement_refs}
                ),
                source_refs=_sources(draft.transport_constraint.source_refs, text),
            ),
            daily_pace=pace,
            visit_requirements=visits,
            time_protections=protections,
            request_sha256=hashlib.sha256(text.encode()).hexdigest(),
            requirements=request.trip_requirements(),
            structured_input_sha256=request.structured_hash(),
            interpretation_origin="model" if text else "skipped_empty",
            named_places=tuple(named),
            requested_place_information=draft.requested_place_information,
            transport_preference=draft.transport_preference,
            semantic_requirements=tuple(semantics),
            subjects=tuple(canonical_subjects),
            discovery_intents=discovery,
            experience_evidence_requests=tuple(evidence[k] for k in sorted(evidence)),
            extraction_issues=(),
        )
    except ValidationError as exc:
        raise RequirementBoundaryError(
            "invalid_canonical_contract", stage="canonical_domain", errors=_errors(exc)
        ) from exc
    return validate_canonical_requirements(result, request)


def assess_requirements(
    contract: InterpretedTripRequirements, *, category_visits=False
) -> tuple[RequirementAssessment, ...]:
    """No registered predicate currently certifies arbitrary open semantic text."""
    linked = {r.requirement_id for r in contract.experience_evidence_requests}
    restriction = contract.transport_constraint
    supported = (
        set(restriction.requirement_refs)
        if restriction and set(restriction.allowed_modes) & {"WALK", "TRANSIT", "DRIVE"}
        else set()
    )
    daily = {
        ref for rule in contract.daily_visit_constraints or () for ref in rule.requirement_refs
    }
    supported |= daily
    from backend.app.policies.category_visits import required_category_visit

    categories = {
        r.requirement_id for r in contract.semantic_requirements
        if category_visits and required_category_visit(r)
    }
    return tuple(
        RequirementAssessment(
            requirement_id=r.requirement_id,
            capability="registered_predicate"
            if r.requirement_id in supported
            else "evidence_assessment"
            if r.requirement_id in linked | categories
            else "semantic_only",
            predicate_id="daily_primary_visit_count"
            if r.requirement_id in daily
            else "allowed_transport_modes"
            if r.requirement_id in supported
            else None,
            predicate_version="1" if r.requirement_id in supported else None,
            evaluation_scope=r.scope,
            evidence_state="not_acquired",
            check_result="unknown",
            disposition="enforce"
            if r.requirement_id in supported and r.strength == "hard"
            else "acquire"
            if r.requirement_id in categories
            else "clarify"
            if r.strength == "hard"
            else "advise",
        )
        for r in contract.semantic_requirements
    )


def require_resolved_hard(assessments: tuple[RequirementAssessment, ...]) -> None:
    unresolved = tuple(a.requirement_id for a in assessments if a.disposition == "clarify")
    if unresolved:
        raise ClarificationRequired("unsupported_hard_requirements", unresolved)
