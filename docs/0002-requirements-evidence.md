# Requirements and evidence

The planner turns a structured brief and optional preference text into source-linked
requirements. Hard obligations constrain generation; soft interests guide supply
without becoming invented quotas. [Configuration](../config/README.md) owns resource
limits, and [itinerary semantics](0003-itinerary-transport.md) owns output counting.

## Request and interpretation

`planning_request_2` carries destination, ISO date-only start/end, a positive integer
traveler count, finite nonnegative Decimal budget with a three-letter uppercase
currency, and optional preferences. Boolean values are not numbers. Blank preferences
become empty; nonblank text retains literal whitespace for provenance.

Structured fields are authoritative. The server uses an Australia/Sydney reference
date for admission, independently of destination/browser timezone. Product accepts
no research reference-date override. Structured-input and full-preference hashes
remain separate.

Empty preferences skip interpretation. Nonempty text enters one shared stage that
separates supported hard requirements, soft wishes, ambiguity, unsupported requests,
safety blocks, provider blocks and system failures. Unsupported hard wording is
never downgraded merely to continue planning.

`daily_pace` has a nullable trip default and unique in-trip date overrides:
ordinary, relaxed, rich or unresolved. Pace is a soft policy; explicit hard counts
have separate authority. Missing legacy pace remains unassessed.

## Input gate and provenance contract

The input gate runs before provider/retrieval resources are initialized.
`preference_input_assessment` is required for current material; missing legacy
assessment remains unassessed. Exact case-sensitive source spans support each
interpretation. Safety blocks precede rewriting or clarification.

| Current format | Responsibility |
| --- | --- |
| `PreferenceDraftV15` / `preference_draft_15` | Provider interpretation wire |
| `preference_prompt_23` | Matching instruction and source projection |
| `interpreted_requirements_6` | Canonical application requirements |

The model cites inclusive integer `first_ref` / `last_ref` references to the
request's Unicode code points. The application restores text, occurrence and
offsets before grounding. Boolean/noninteger, out-of-range or reversed references
fail with field paths; no guessed correction retry repairs an invalid input gate.
Complete supporting substrings, including whitespace boundaries, remain necessary.
The request-bound map and hashes are application-owned.

DTO, prompt, source reader and capture revisions must agree before sending.
Compact UTF-8 JSON preserves source strings, and schema inventories reflect actual
input counts. Explicit historical readers retain draft 13/14, quote-occurrence and
canonical 3–5 formats without silently upgrading their provenance.

Supported issue types include structured-field conflicts, independently sourced
hard contradictions, unsupported capabilities, ambiguity and non-travel controls.
Missing or invalid provenance is a system contract failure, not traveler ambiguity.
Failure artifacts retain allowlisted categories, codes, stages, field paths and
requirement IDs; they exclude raw quotations and provider payloads.

## Evidence ownership

| Source | Can establish | Does not establish |
| --- | --- | --- |
| Places | Supplied identity, coordinates, categories and applicable operating fields | Booking, admission or future availability without evidence |
| Weather | Available daily forecast for its recorded window | Historical weather or an invented hourly fallback |
| Routes | Directed, mode/time-applicable provider observations | Unqueried departures, modes or access guarantees |
| Official web | Source-bound claims with authority and date/subject applicability | Completeness from an unsuccessful search |
| Reviews/Profile | Bounded visitor-experience observations | Official rules or universal suitability |
| TripWorld | Retrieval identity, geography and static descriptive categories | Current Google verification or operating facts |

GeoDB suggestions assist input only; their IDs are not planning evidence.
Conflicting, unavailable and unobserved facts remain distinct.

## Dated total primary visit counts

`daily_visit_constraints` expresses source-linked date, exact/minimum, nonnegative
integer target and hard/soft strength. A current empty list means assessed absence;
a missing historical field does not. Count primary experience occurrences on each
date, independently of named/category obligations. Separate occurrences at one venue
count separately. Meals, transport, free windows and Nearby do not count.

Unknown roles or dates produce lower/upper bounds rather than zero. Diagnostics
retain PASS/FAIL/UNKNOWN. V0 uses declared/name-proxy observations; tools versions
use their qualified semantic ledger. Contradictory hard totals, or a positive count
on a fully protected date, require clarification.

Hard totals govern quantity on their date. A minimum remains a lower bound, not an
exact target. Explicit zero exempts minimum sightseeing coverage but does not forbid
meals/travel; full-day time protection is a separate constraint. Independent evaluation
uses separately reviewed obligations rather than planner deductions.

## Semantic qualification and multiplicity

Semantic goals retain strength, polarity, subject, scope and source references.
Canonical references deduplicate equivalent goals. Unknown subjects are not promoted
to whole-party requirements, and historical themed wording is not retroactively
upgraded to a stronger goal.

A positive, count-free POI interest normally targets one distinct visit; a sourced
focus may target two. Explicit counts, dates, exclusions and exclusive scopes take
precedence. Broad wishes such as a pleasant trip create no visit quota. One eligible
POI may serve several goals; repetition does not manufacture distinct fulfillment.

V1–V3 assess factual-gate candidates for principal-role eligibility, permitted
exceptions and per-requirement relationships. Ordinary cafes/offices are not main
visits without a supported exception. Related alternatives are not fulfillment.
Every supplied identity must receive exactly one valid result; foreign/duplicate/
missing references fail. Judgments must cite that candidate's evidence.

Assessment caches bind identity, evidence, requirements, exceptions and prompt/schema
versions. One bounded reference correction is available only for supported reference
errors; other terminal failures remain failures. Unknown assessment grants no authority.
Unrequested canonical repetition is a policy violation; explicit minimums do not
become maximums. Exception allowances apply per goal across alternatives, not per POI.
Historical unassessed multiplicity is not a passing assessment.

### Required category visits

Supported positive, whole-party hard category requests retain ordinary trip scope,
explicit exact/minimum counts and distinct-date conditions. Access, crowding and
other conditions remain separate obligations. Matching uses supplied place evidence,
not a destination/category vocabulary hardcoded in the application. V0 has no grounded
category-enforcement claim.

Reserve hard candidates ahead of soft interests. Count only supported eligible main
visits actually scheduled. Exact counts with unresolved potential extras remain
uncertain; a known minimum can pass once enough visits are established. V3 protects
attained hard count/date coverage and can repair proven shortfalls. Partial discovery
or no match is not proof that the request is impossible.

## Admission, acquisition and deterministic supply

1. Discover user-named places first, then general attractions and bounded landmark
   nominations. RAG joins the same canonical pool and capacity.
2. Admit required identities first, then rotate intents using cheap geographic and
   eligibility checks. Compatible successful Details may be reused; sends, successes
   and failures retain separate counters without hidden retries.
3. Qualify acquired candidates. If filtering removes apparent opportunities, continue
   the same bounded queue without resetting counters or processed identities.
4. Build supply deterministically: protect required/excluded obligations, rotate
   linked goals, consider supported alignment/conflicts and geographic diversity,
   then use stable tie-breaks. Unknown profiles abstain; ratings break ties only when
   all compared candidates have them. Cosine is not a quality reward or RAG quota.

Exploration allocation spans admission, acquisition and supply. Mixed origins use one
canonical slot; an empty lane releases capacity. Exclusive scopes and shared exception
allowances remain binding. Budget stops are resource outcomes, not unsuitable-place
judgments. A model subset selector is not a runtime dependency.

Product capacity reflects duration, pace, protected dates and hard obligations under
the selected resource profile. Ordinary shortfall does not create traveler ambiguity;
required-capacity exhaustion is explicit failure. See
[capacity policy](../backend/app/policies/poi_capacity.py) and
[resource profiles](../config/README.md#product-acceptance-profile).

## Forecast, operating facts and official web

Open-Meteo daily forecasts retain unavailable dates without historical/hourly
substitution. Current and regular opening periods remain separate; neither certifies
holiday access, tickets or reservations.

Official-information tasks follow typed requested-place needs and concrete risks in
the final shortlist. Priority is explicit residual needs, other named explicit needs,
required-place risks, other named risks, then remaining selected-place risks.
Tasks deduplicate identity/need/date/subject and merge facets. A bounded reasoner
retains claim authority/applicability and conflict; no found exception does not mean
no exception exists. Prefer applicable official facts over structured provider facts,
recent web observations and visitor/community context for the same claim.

## Discovery and identity

Named-place correspondence runs after directed search and before admission. The
model judges same/different/unresolved using the user's qualifiers and supplied
names, addresses, coordinates and search facts. Adoption requires complete valid
coverage, one supported match and no unresolved competitor. A singleton or top rank
is not proof; lexical alias patches cannot replace correspondence. Provider/resource
failures remain system outcomes.

Destination-only landmark nomination is one auxiliary V1–V3 call after the input gate.
It contributes model-origin names/ranks, not required visits. Invalid/empty responses,
provider failures and timeouts can degrade to the existing qualified pool; cancellation
propagates. This fallback does not cover terminal identity/semantic failures.
Compact numeric traces distinguish estimates from reported usage and omit raw prompts.

## Failure and observability

Malformed input, safety/provider blocks, clarification, resource exhaustion and
contract failure retain distinct outcomes. Numeric traces and allowlisted failure
artifacts explain the stopped stage without exposing private source text. Clear
requirements are not rewritten to disguise missing evidence or exhausted capacity.

## Calendar support versus same-day remaining-time planning

The server accepts starts from today through today + 13 days and at most ten inclusive
trip days. `GET /api/planning/date-window` exposes this policy without initializing
providers. The frontend bounds the end date by both start + 9 and the server window;
backend validation remains authoritative. Same-day remaining-hour planning is unsupported.
