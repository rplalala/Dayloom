# Reliable Trip Plan Agent: Project Proposal

**Project:** Capstone / Thesis B travel-planning system

**Document date:** 2026-10-04

**Status:** Engineering proposal aligned with the implemented baseline

**Scope and status authority:** [PROJECT.md](../PROJECT.md)

## 1. Executive summary

Reliable Trip Plan Agent supports travelers in turning trip details and personal
preferences into structured, inspectable itineraries. Its central engineering
challenge is to coordinate language-model proposals with user requirements,
external evidence and scheduling constraints. A plausible narrative alone does
not establish that places, opening conditions, transport or costs are supported.

The system maintains four independently runnable versions: V0 provides plain LLM
planning; V1 adds external information and tools; V2 adds retrieval-augmented
discovery; V3 adds validation, targeted repair and re-validation. The traveler-facing
Product application uses V3. A separate Developer surface and CLI entry points
preserve access to V0-V3. An independent evaluation package assesses submitted
artifacts without treating the planner's own verdicts as factual ground truth.

This proposal defines users, intended value, user stories, requirements, technical
approach and engineering acceptance. It describes an existing implementation
baseline and identifies outstanding work. It does not claim that V3 outperforms
earlier versions, that development checks establish real-world reliability, or that
a formal comparative study has been completed.

## 2. Problem definition

Trip planning requires decisions across information sources with different
identities, coverage and temporal applicability. A traveler may also express
mandatory visits, exclusions, protected time and qualitative interests in the
same request. Three failure modes motivate the project:

1. **Intent distortion:** a planner can omit an explicit obligation, invent a hard
   quota from an ordinary interest, or silently reinterpret an unsupported condition.
2. **Unsupported feasibility:** a relevant place or fluent itinerary can be mistaken
   for evidence of applicable opening conditions, affordable cost or feasible travel.
3. **Unsafe correction:** repairing one conflict can introduce another, remove a
   protected commitment or discard an earlier accepted improvement.

The project addresses these risks through explicit contracts, normalized evidence
and application-controlled validation and adoption. In this proposal, reliability
means traceable handling of supported requirements, evidence and corrections.
It does not mean guaranteed availability, admission, booking or total affordability.

The problem statement is grounded in project design and development observations.
It is not a claim about the prevalence of these failures across all travel-planning
products, and no completed user study or literature-derived novelty claim is implied.

## 3. Aim and objectives

The aim is to build a maintainable planning system that supports useful traveler
decisions while making its factual and operational limits inspectable.

| ID | Objective | Engineering evidence of achievement |
| --- | --- | --- |
| O1 | Preserve traveler intent | Authoritative trip facts and explicit obligations retain their source; ambiguous or unsupported hard conditions remain explicit |
| O2 | Separate proposals from evidence | Normalized observations retain identity, source and applicability; missing facts do not become confirmed claims |
| O3 | Support bounded correction | V3 adopts permitted edits only after re-validation and preserves safe accepted state |
| O4 | Preserve mechanism isolation | Each V0-V3 entry point runs independently without silently acquiring later-version mechanisms |
| O5 | Support independent assessment | Submitted artifacts, reviewed obligations, independent observations and anonymous human judgments remain distinguishable |

These objectives define engineering acceptance. Their existence or implementation
does not establish a measured comparative benefit.

## 4. Users, stakeholders and scope

### 4.1 User roles

The following roles describe consumers of the implemented system; they are not
personas derived from interviews or evidence of market demand.

| Role | Primary need | Interaction boundary |
| --- | --- | --- |
| Traveler | Create and review an itinerary that respects stated trip details and communicates uncertainty | Product input assistance, planning and itinerary presentation |
| Developer | Diagnose behavior and verify version-specific mechanisms | Developer interface, independent runners, configuration and diagnostic artifacts |
| Researcher or evaluation operator | Prepare source-linked artifacts and inspect independently assessed outcomes | Evaluation intake, evidence review, offline scoring and report workflows |
| Human reviewer | Judge anonymous itinerary alternatives without version or automatic-score cues | Blinded review package and revision-aware answer submission |

### 4.2 Included scope

The engineering baseline includes structured requests, optional preference
interpretation, itinerary generation, normalized external evidence, V2/V3 retrieval,
V3 validation and repair, Product/Developer interfaces and approved evaluation
Tickets 01-12. These include independent final-output scoring and anonymous review,
V3 draft/final-primary diagnostics, isolated frozen V3 Repair replay, and selected-source
mechanism reporting. Detailed contracts and dated acceptance records define
the exact delivered subsets.

### 4.3 Excluded scope

The project does not provide booking or payment transactions, guaranteed factual
availability or affordability, user accounts or saved itinerary history, or a
production multi-user service guarantee. Automatic corpus rebuilding and new
distributed infrastructure are outside the current design.

Formal benchmark construction, live evidence collection, comparative experiments,
thesis writing and final research conclusions require
separately approved work. This proposal adds no live acquisition or execution budget.

## 5. Principal user journeys

**Traveler journey:** enter destination, supported dates, traveler count and a
whole-trip budget/currency; optionally provide or polish preferences; review and
explicitly apply any polishing suggestion; submit the request; observe progress or
stop the run; review a successful itinerary and its uncertainty. Invalid input and
unsupported hard conditions retain the existing rejection or clarification boundary.
The system does not silently substitute a different request.

**Engineering journey:** run versions independently against a valid request,
inspect structured outputs and diagnostics, reproduce a failure at the relevant
seam, and validate a scoped correction. Side-by-side development inspection is not
a formal version-comparison experiment.

**Evaluation journey:** explicitly select and submit source-linked artifacts,
review obligations and ambiguous associations, supply independent observations,
replay implemented scorers, and inspect availability alongside outcomes. Anonymous
human review is a separate judgment channel. Final-quality scoring reads saved outputs.
For a separately supplied controlled case, the operator can execute the actual V3
post-primary path with frozen offline capabilities and inspect independent target/control
outcomes. These workflows do not automatically choose cases or certify a benchmark.

## 6. User stories and acceptance criteria

The stories below express user value and observable contract conditions for the
implemented engineering baseline. They are not new tickets or a claim that every
condition has been validated with live providers. Evidence and remaining limits
belong to the linked design and acceptance records.

### 6.1 Traveler stories

| ID | User story | Acceptance criteria |
| --- | --- | --- |
| US-01 | As a traveler, I want to enter my trip details once so that the plan reflects the trip I intend to take. | Destination, supported ISO dates, traveler count and whole-trip budget/currency are validated. Form facts remain authoritative; interpretation does not replace them. |
| US-02 | As a traveler, I want required visits, exclusions and interests to retain their distinct meanings so that the planner does not invent or weaken my priorities. | Explicit obligations retain source and subject provenance. Ordinary interests remain soft goals. Unsupported or ambiguous hard conditions remain explicit rather than being silently accepted. |
| US-03 | As a traveler, I want a readable daily itinerary so that I can distinguish scheduled commitments from optional ideas. | Successful output separates dated/timed primary activities, transport and optional Nearby references. References do not satisfy required visits or add scheduled occupancy or cost. |
| US-04 | As a traveler, I want estimates and missing information to be identifiable so that I can judge which details need independent confirmation. | V0 transport remains explicitly estimated; V1-V3 transport is application-owned. Missing or inapplicable route, opening, weather or cost evidence is not presented as confirmation. |
| US-05 | As a traveler, I want supported contradictions to be addressed without losing protected commitments so that corrections preserve the intent of my trip. | V3 edits stay within authorized targets and permissions, are re-validated before adoption, and retain safe accepted state when a proposed change fails acceptance. Unresolved facts remain unresolved. |
| US-06 | As a traveler, I want optional input assistance under my control so that I can decide whether a suggested revision reflects my intent. | Destination suggestions allow manual entry. Preference polishing offers preview, Apply/Dismiss and Undo, does not auto-submit, and remains subject to the planning input gate. |
| US-07 | As a traveler, I want honest progress and a way to stop planning so that I can control a long-running request. | Progress reflects observed workflow position. Stop/error does not show successful completion; stale responses cannot replace a newer request's result. Local cancellation does not guarantee cancellation or billing reversal at an external provider. |

### 6.2 Developer and evaluation stories

| ID | User story | Acceptance criteria |
| --- | --- | --- |
| US-08 | As a developer, I want to run V0-V3 independently so that I can inspect a mechanism without replacing earlier versions. | Separate runners remain available. V0 has no external travel acquisition or RAG; V1/V2 do not invoke V3 repair. Diagnostics remain separate from the Product presentation contract. |
| US-09 | As an evaluation operator, I want submitted artifacts and obligations to retain their provenance so that an assessment can be traced to its actual inputs. | Original artifact identity and hashes are preserved. Projection and reviewed associations retain source references; scoring does not rewrite original results or use planner verdicts as ground truth. |
| US-10 | As an evaluation operator, I want evidence availability reported alongside compliance so that missing facts do not create misleading scores. | Implemented scorers expose applicable populations, denominators and UNKNOWN outcomes. The snapshot primitive accepts supplied transport; the installed automatic evaluator supplies fresh bounded acquisition with frozen inputs, receipts and offline replay. A formal collection campaign still requires separate authorization. |
| US-11 | As a human reviewer, I want anonymous itinerary alternatives so that my judgment is recorded separately from version attribution and automatic scores. | Review material hides version attribution and automatic scores. The researcher holds the mapping; imported answers retain package/rater/revision context and human preferences remain separate from automatic metrics. |
| US-12 | As an evaluation operator, I want to compare a saved V3 draft with its final primary plan so that I can inspect changes and their independently assessed outcomes. | Same-run source lineage, paired masks/deltas and independent continuity remain separate. Missing stages or unresolved correspondence remain visible; the draft is not an independently executed V2 result. |
| US-13 | As an evaluation operator, I want to replay a supplied V3 Repair case under frozen capabilities so that I can inspect detection, adoption and independently reviewed target/control outcomes. | The real post-primary path recomputes permissions. Script mismatches fail replay integrity; lawful changes, regressions and unresolved evidence remain distinct. No formal case corpus is generated. |
| US-14 | As an evaluation operator, I want source-linked mechanism observations so that I can inspect triggers, attempts, adoption and internal progress separately from independent quality. | Selected-source hashes and observation coverage are retained. Default-off capture observes existing seams without changing generation; missing observations remain unavailable. |

## 7. Requirements and traceability

### 7.1 Functional requirements

| ID | Required capability | Stories | Detailed owner |
| --- | --- | --- | --- |
| FR-01 | Validate structured trip facts and preserve interpreted preference provenance | US-01, US-02, US-06 | [Requirements and evidence](0002-requirements-evidence.md) |
| FR-02 | Produce structured itineraries with distinct primary, reference and transport roles | US-03, US-04 | [Itinerary and transport](0003-itinerary-transport.md) |
| FR-03 | Acquire and normalize bounded external evidence for V1-V3 | US-04 | [Requirements and evidence](0002-requirements-evidence.md) |
| FR-04 | Discover V2/V3 candidates through compatible persistent retrieval, identity resolution and admission | US-03, US-08 | [Retrieval and persistence](0004-retrieval-persistence%28v2v3%29.md) |
| FR-05 | Validate and apply only permitted, re-validated V3 corrections | US-05 | [Validation and repair](0005-validation-repair%28v3%29.md) |
| FR-06 | Provide controlled input assistance, progress, cancellation and separate Product/Developer disclosure | US-06, US-07, US-08 | [Application and operations](0007-application-operations.md) |
| FR-07 | Maintain independent version entry points and orchestration boundaries | US-08 | [System architecture](0001-system-architecture.md) |
| FR-08 | Assess submitted artifacts through independent final/paired scoring, anonymous review, frozen controlled Repair and mechanism reporting | US-09 through US-14 | [Independent evaluation](0006-independent-evaluation.md) |

### 7.2 Quality requirements

| ID | Quality requirement | Verification approach and boundary |
| --- | --- | --- |
| QR-01 | Traceability and honest uncertainty | Inspect source/evidence references and test missing, contradictory and inapplicable observations; schema validity is not factual truth |
| QR-02 | Version isolation and maintainability | Test version-specific dispatch and shared contract regressions through independently runnable paths |
| QR-03 | Bounded resource use | Test configured allowances, exhaustion and cancellation; use measured diagnosis for tuning rather than an invented latency or cost target |
| QR-04 | Safe resource lifecycle | Test partial setup, completion, errors and cancellation with owned clients/connections; external work may already have been dispatched |
| QR-05 | Controlled information disclosure | Check the Product allowlist and text rendering; credentials, prompts and raw provider/model material remain outside the traveler response and version control |
| QR-06 | Consistent interaction | Test request invalidation, stale-result rejection, date/currency controls, keyboard interaction and narrow-screen rendering |
| QR-07 | Independent, reproducible assessment | Replay saved source-linked artifacts and versioned rules; availability, unresolved associations and human judgments remain visible |

These are contract-level acceptance conditions. They do not introduce production
service-level commitments, an account-wide billing limit, or a promised factual
success rate.

## 8. Technical approach

The [system architecture](0001-system-architecture.md) defines the modular monolith,
independent V0-V3 mechanisms and model/application responsibility boundary.
[Retrieval](0004-retrieval-persistence%28v2v3%29.md) contributes discovery candidates;
[V3 validation and Repair](0005-validation-repair%28v3%29.md) governs permitted corrections.
The functional traceability table above connects user needs to those detailed owners.

## 9. Development and validation approach

Development uses scoped changes, proportionate checks and review.
[Dated records](records/README.md) distinguish implementation from observed validation and
approved freezes. Routine external-boundary tests use fixtures or mocks; live pilots need
an approved attempt and budget.

The [independent evaluator](0006-independent-evaluation.md) assesses selected original
artifacts using reviewed obligations and separately sourced observations. Its implemented
workflows do not establish a formal dataset, sampling protocol or comparative conclusion.
Formal evaluation requires a separately approved collection scope, budget and analysis plan.

## 10. Deliverables and delivery gates

| Deliverable | Current state | Acceptance or next gate |
| --- | --- | --- |
| Independently runnable V0-V3 | Implemented baseline with recorded engineering validation | Preserve version boundaries and pass checks relevant to each approved change |
| Product and Developer interfaces | Implemented, including input assistance and Product V3 presentation | Validate interaction and disclosure against their defined contracts |
| Evidence, retrieval and V3 correction components | Implemented within bounded contracts | Verify provenance, compatibility, permitted edits, adoption and failure behavior |
| Independent evaluation Tickets 01-12 | Approved offline implementation, review and engineering delivery scopes completed | Preserve source-linked acceptance and separately authorize real collection, formal cases, assessment and analysis |
| Project proposal, core design, ADRs and engineering records | Maintained repository assets | Keep user value, technical ownership, current status and dated evidence consistent |
| Formal comparative evaluation and thesis outputs | Outside current execution scope | Separate authorization and an approved research plan |

Delivery is dependency-based. Calendar commitments and effort estimates have not
been agreed. Completion of a package does not automatically authorize the next,
freeze a version or publish repository changes.

## 11. Risks and mitigations

| Risk | Mitigation | Residual limitation |
| --- | --- | --- |
| Stale or incomplete evidence | Retain provenance, temporal applicability and UNKNOWN | No universal freshness or availability guarantee |
| Ambiguous intent or identity | Preserve source, apply strict admission and retain clarification/review boundaries | Some requests and associations remain unresolved |
| Model contract failures | Validate outputs and constrain correction scope | Generation or patch failure remains possible |
| Correction regressions | Enforce permissions, component consistency, re-validation and fallback | Unsupported facts cannot be repaired into verified evidence |
| Resource exhaustion or variable latency | Bound requests, expose availability and diagnose measured bottlenecks | External latency, incomplete usage and dispatched work remain outside full local control |
| Retrieval incompatibility | Use compatible corpus/vector manifests and persistence checks | Exact regeneration depends on retained vectors and provider behavior |
| Evaluation leakage | Separate independent observations, automatic scores and researcher-held blind mappings | Formal collection and review conduct need their own controlled plan |
| Documentation drift | Maintain one current owner per responsibility and dated historical records | GitHub state and published repository revisions must be checked when work resumes |

External acquisition, attribution and retention requirements depend on the actual
provider and use context. The architecture does not by itself establish that all
external terms have been verified. Private raw captures are not published project
deliverables.

## 12. Engineering success criteria

The engineering deliverable is accepted when the relevant approved scope can
demonstrate that:

1. Valid requests retain authoritative facts and explicit preference boundaries.
2. Successful itineraries preserve role separation and do not disguise missing
   evidence as confirmation.
3. Each version runs independently with its intended mechanisms.
4. V3 adopts only permitted corrections that satisfy its acceptance checks.
5. Product and Developer interactions respect lifecycle and disclosure contracts.
6. Implemented evaluation outputs retain provenance, denominators, availability
   and independence from planner self-judgment.
7. Relevant checks pass, review findings are resolved, and remaining limitations
   are documented with their actual evidence scope.

These criteria support engineering acceptance, not a blanket certification of
travel feasibility or a final research conclusion. Historical validation evidence
is indexed through PROJECT.md and the records below; writing this proposal does
not rerun or extend it.

## Project references

- [Current scope, implementation status and limitations](../PROJECT.md)
- [Core designs, detailed contracts and architecture decisions](README.md)
- [Runtime configuration](../config/README.md)
- [Development commands](guides/development.md)
- [Dated engineering and acceptance evidence](records/README.md)
- [Evaluation package interfaces](../backend/evaluation/README.md)
- [GitHub evaluation specification and task hierarchy](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12)

These references establish project traceability. A formal academic bibliography
or institution-specific thesis proposal remains separately scoped source work.
