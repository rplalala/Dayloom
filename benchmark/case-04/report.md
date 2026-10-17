# Case 04: Singapore weekend

Revision 2 completed one generation each in V0 → V1 → V2 → V3 order, followed
by one Primary evaluation on 15 October 2026. All native invocations exited 0.
Primary processing and acquisition are complete, evidence is decidable, and all
live processes have ended. The researcher accepted the Primary results and,
after the offline candidate/relevance, same-run Repair/pair and resource analysis,
the [complete automatic case and its limitations](#acceptance) on 15 October 2026.
Local main-worktree integration is complete; blinded human review is deferred
and case-14 is waiting.
[Issue #153](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/153)
owns the live state under
[batch #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151).

## Request and selected sources

The [unchanged request](../inputs/case-04.json) covers Singapore on
17–18 October 2026, two adults and a whole-group SGD 800 budget. Gardens, major
city sights and views are independently matchable interests. Fairly full days
support a rich pace without an exact visit quota. The whole-trip hard transport
restriction allows only WALK and TRANSIT.

The actual application reference date was 15 October in Australia/Sydney; the
Saturday/Sunday request passed its date gate. Independent IANA review established
Asia/Singapore and UTC+08:00. Submitted time strings were retained.

| Binding | SHA-256 or revision |
| --- | --- |
| Live source revision | `941f4986be876dbb4586e8a34ec156f89630f755` |
| Integrated PR [#166](https://github.com/rplalala/Reliable-Trip-Plan-Agent/pull/166) | `72b6f0ec724954e4520a50d7b16b354bcd9ab131` |
| Original input | `06ea61ff07fed40a3abef8c7bbbc42676f99d7d28db4805efd5f627afa4be4b7` |
| Runtime configuration | `a6c932272e8d5037ed66fb057e629f8dcff44f3e12117d2dbcb16c8905454058` |
| Reviewed requirements | `15f0935a215b767fff033b0fe0048df72231e12f0cb1c22cf2d16f7aecf14f4f` |
| V0 selected result | `539d12725d3a98966cf05f726969a3a830ccc6f7900d0c04a3c73f61cdd0aad4` |
| V1 selected result | `f018e695651ef51d6e106f63ee2ac1ee1f432cd6d5cc60796cd1211dca1f12ff` |
| V2 selected result | `2b1161d9cfd459ea5310f68700db8e92142f41d142bfdb9269d88a022bf12056` |
| V3 selected result | `ccc8fcc81fc9aa3027d3ffd3de8d49091568465389d5cd3977faaf86f3e021a4` |
| Accepted material manifest | `8da8ddd6ebc4d82e5048cc84f8a0f308041d24ea901286b1ef9ce73f4815a3f6` |
| Primary preparation content | `f4ec83861d82a25b8f3d6005c8bec77bcc48fedea29599f8d262100363b78e91` |
| Primary native report | `c442387fa92f4ed2e263dfaa39faf0deb809259203f22d52e3025a0bd5103b1f` |
| Primary closed receipt | `76ec7c18bdbea13f37cf59bc7b299182f34b5e860e286c466fe6365cd44a2c8d` |

The selected backend, tools, runtime and dependency lock matched PR #166.
No implementation, request, credentials or runtime configuration changed during
this attempt. The final case-report commit is separate from the frozen live source.

## Primary results

All five common dimensions apply: requirements, grounding, non-overlap, opening
and routes. The pre-density score is their unrounded rational mean of verified
PASS fractions. The overall score subtracts the mean daily density deduction,
with a floor of zero.

| Version | Five-dimension score | Mean density deduction | Overall score | Main visits by day |
| --- | ---: | ---: | ---: | --- |
| V0 | 95.5 | 70 | **25.5** | 5 / 5 |
| V1 | 100 | 50 | **50** | 4 / 5 |
| V2 | 100 | 30 | **70** | 4 / 4 |
| V3 | 100 | 0 | **100** | 3 / 3 |

The existing [rich density profile](../../docs/contracts/0005-quality-human-review.md#daily-density)
applied daily deductions of 0, 30 and 70 points for three, four and five confirmed
primary visits respectively. These are the saved evaluator's rules; the request
does not acquire an exact-three-visits obligation. Density remains a separate
adjustment rather than another hard requirement.

The following counts are PASS / FAIL / UNKNOWN:

| Dimension | V0 | V1 | V2 | V3 |
| --- | --- | --- | --- | --- |
| Hard requirements | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 | 1 / 0 / 0 |
| Grounding | 10 / 0 / 0 | 9 / 0 / 0 | 8 / 0 / 0 | 6 / 0 / 0 |
| Non-overlap | 18 / 0 / 0 | 16 / 0 / 0 | 14 / 0 / 0 | 10 / 0 / 0 |
| Opening | 9 / 1 / 0 | 9 / 0 / 0 | 8 / 0 / 0 | 6 / 0 / 0 |
| Routes | 7 / 1 / 0 | 7 / 0 / 0 | 6 / 0 / 0 | 4 / 0 / 0 |

The WALK/TRANSIT hard restriction passed in all four versions. The equivalent
route policy has one scoring owner in requirements, avoiding duplicate penalties.

V0 has two independently evidenced failures:

- The second-day `day2_kampong_glam` visit contains 3,600 seconds confirmed outside
  the associated venue's current opening hours.
- Singapore Botanic Gardens → National Gallery Singapore has 1,800 scheduled
  seconds against a 2,596-second independent transit duration: a raw deficit of
  796 seconds, exceeding the 300-second schedule tolerance.

The original V0 notes describe the Kampong Glam stop as a precinct visit, with
interior access unverified. Its saved opening verdict checks the associated
venue's API hours; applicability to exterior or neighborhood viewing has not
received a new adjudication. The accepted result retains this limitation and
the original verdict. The density deduction also retains its existing count-based
policy rather than establishing that five visits necessarily make a day infeasible.

There are no UNKNOWNs, unresolved denominators or acquisition failures in this
Primary report. Missing-hours assessment was enabled and checked before scoring,
but had zero eligible cases, so no access-model call was sent. Opening checks
therefore use API hours rather than model-supported access judgments. Independent
route coordinates came from the evaluator's identity snapshot, not Planner data.

The saved rule identities are `rtpeval_verified_quality_2`,
`rtpeval_requirement_schedule_rules_4`, `rtpeval_route_rules_3` and
`rtpeval_daily_density_2`. These single-attempt observations are not a general
version ranking or a causal Repair result.

## Candidate process and same-run Repair

The [complete submitted itineraries](itinerary.md) retain all four final schedules
and a reference view of the V3 draft with declared provenance-token sanitization.
The [material index](material-index.json)
binds reader data to original source hashes. These public views are separate from
the private native replay bundles.

The [candidate-process report](analysis/poi-process/report.md) observes V1/V2
discovery counts of 62/73, admission of 48/48, enrichment of 20/48, supply of
10/10 and independent final scheduling of 9/8 canonical places. V2 discovery is
partial because the saved RAG observation is partial. Its observed discovery set
contains 54 Google-only, 12 RAG-only and seven mixed-origin places. Three RAG-only
places reached admission/enrichment; none reached supply or the final itinerary.
Four mixed-origin places were supplied and scheduled. Complete later-stage set
differences and partial discovery differences retain separate meanings.

One additional independent, result-blind review covered 94 candidate venues
against three source-only interests. Only 19 venues had independent Primary
metadata. The 282 judgments contain seven relevant and 275 UNKNOWN outcomes;
missing evidence does not imply irrelevance. All relevance-stage measurements
remain partial, so exact relevance gains and conversion comparisons are unavailable.

The [Repair report](analysis/repair/report.md) distinguishes separate V2/V3
generations from the same-run V3 draft/final pair. V3 used three deterministic
deletion rounds and no Repair model send. It removed Gardens by the Bay,
Marina Barrage and Singapore Botanic Gardens, reducing primary visits from 5/4
to 3/3. Retained activity fields are unchanged. Fort Canning Park remains, but
the score alone does not establish that the requested interests were preserved.

The [same-run paired report](evaluation/v3-pair/summary.json) applies the same source-bound missing-hours
access policy to the original V3 draft and final-primary stages. Saved Google
observations retain their exact provenance; eligible access gaps receive a fresh
assessment. Identical activity/time/evidence contexts share one decision. Primary
scores, original activities and factual API-hours coverage are unchanged.

| Same-run stage | Overall / 100 | Auxiliary / 100 | Density deduction | Opening P / F / U | Route UNKNOWN |
| --- | ---: | ---: | ---: | --- | ---: |
| Draft | 44.285714 | 94.285714 | 50 | 9 / 0 / 0 | 2 |
| Final primary | 100 | 100 | 0 | 6 / 0 / 0 | 0 |

The paired overall change is **+55.714286 percentage points**.
The 17 October 2026 refresh used no model calls, zero Google sends
and zero retries, for **USD 0** reference cost. Native source, model-response
and receipt replay passed offline. Model-supported access is not certified opening
hours, and the paired mask remains separate from the historical primary mask.
Removed visits and denominator changes do not prove repair of their old facts.
No eligible access gap was present, so no model assessment was needed; missing
route observations remain UNKNOWN.

The [shared refresh record](../../docs/records/evaluation/v3-pair-report.md#paired-access-refresh-2026-10-17)
owns the execution limits and provenance. Original evidence and historical reports
remain retained; this current view replaces the earlier paired presentation.

The two draft route UNKNOWNs through Marina Barrage lack compatible saved
observations and disappear with deleted visits. Their disappearance is not a verified
route fix. The overall difference includes a 50-point density change.

## Observed execution and reference consumption

| Stage | LLM / embedding calls | Observed tokens | Google sends | Conservative reference USD | Allowance USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 2 / 0 | 28,793 | 0 | 0.008247720 | 0.99 |
| V1 | 4 / 0 | 52,646 | 50 | 1.347388844 | 8.00 |
| V2 | 5 / 1 | 54,247 | 90 | 2.182535518 | 9.00 |
| V3 | 4 / 1 | 51,681 | 65 | 1.682182954 | 12.00 |
| Primary | 1 / 0 | 20,109 | 69 | 1.275436560 | 10.00 |
| New attempt | 16 / 2 | 207,476 | 274 | **6.495791596** | **39.99** |

Generation token totals include the two embedding calls, with 9 and 10 tokens.
Primary used 19,175 input and 934 output tokens, including 19,172 cache-write
input tokens. Its 69 Google sends comprised 21 searches, 24 details calls and
24 route matrices, with 24 billable matrix elements. Each V1–V3 generation
recorded 117 matrix elements. Native backing HTTP observations are not charged
again as separate model requests. There were no Repair model sends, automatic
retries or unpriced recorded events.

Generation guards elapsed 80.734, 129.157, 149.547 and 132.140 seconds respectively,
below their individual 600-second limits. Primary took 27.601 seconds natively
and 39.062 seconds under its 1,200-second process guard. Execution session and PID
checks confirmed that all owned processes ended.

The historical failed attempt retains USD 0.001477615 at its original reference
basis. The mixed historical/current planning ledger is therefore USD 6.497269211.
The new authorized maximum plus historical consumption was USD 39.991477615,
within the original USD 40 case ceiling.

New model estimates use conservative published EU Standard rates checked on
15 October; Google and embedding estimates retain published retail assumptions.
The original native generation cost files retain their own Global Standard basis.
Current [model](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Foundry](https://azure.microsoft.com/en-us/blog/gpt-6-astra-sol-and-luna-for-production-agents-in-microsoft-foundry/)
and [Google](https://developers.google.com/maps/billing-and-pricing/pricing)
sources support reference planning. Actual account invoices and external Codex
usage/billing are unavailable.

The [resource view](analysis/resources/report.md) includes the historical failure,
four revised generations and Primary: 17 LLM calls, two embedding calls,
219,615 observed tokens and 296 backing HTTP sends. The seven external semantic
tasks remain a separate allowance. Reused paired observations are not charged
again, and failure/success timings are not pooled as a common latency cohort.

The selected plan used existing controls and operational cost checks between
versions. Generation has no cumulative monetary admission guard. Additional
interpretation/V0 token and time caps remained unselected proposals. Primary
enforced USD 10, 250 Google sends, 64,000 input / 8,192 output tokens,
90 seconds per request, at most two model sends and zero retries.

## Preparation and preservation checks

The fresh source-only author and independent reviewer resolved the original
transport clause as whole-trip `transport_modes`, allowing WALK and TRANSIT.
They reviewed the three interests, rich/no-quota density and Singapore time
context without reported result exposure. A distinct result-dependent reviewer
then checked the 33 submitted nontransport final activities; all remained
committed. The exact source dictionaries and original strings were preserved.
All four reviewed contexts were checked inside the frozen Primary package.

The four selected producer completions passed attachment/finalization and native
intake. Intermediate registrations were blocked while later versions were
unstarted; each completed version was qualified independently. Passive V1/V2
opportunity capture and full same-run V3 draft/final evidence support the offline
process observations above.

Focused existing regressions covered hard transport, requirement wire,
compatibility, initial mixed routes, V0 acceptance, V3 mixed transport and
requirement/schedule evaluation. The initial run had 79 passes and 68 sandbox
temporary-directory setup errors. The affected file then passed all 70 tests
unchanged using a fresh workspace-owned temporary directory: 147 unique tests
passed. This was a targeted check, not a full-suite claim.

Date/schema, editable imports, pinned tokenizers and actual read-only RAG
connection/manifest/embedding-space compatibility checks passed. Database writes
and corpus rebuilds were excluded. Final checks verified the Primary's closed
222-file receipt, all four generation key-hash sets, the unchanged 125-file
historical failure package and the exact previous report snapshot. The requested
verification also confirmed native intake and implementation hashes against the
frozen preparation, and checked the five-dimension mean, daily density deductions
and overall score arithmetic for all four versions. These Primary acceptance
checks preceded the separately authorized offline follow-up analysis; the
accepted Primary report and original evidence remain unchanged.

All five offline native reports (population, opportunities, relevance, Repair and
resources) were rebuilt from a fresh archive restoration and matched their saved
reports exactly. This also passed independently after transfer to the main
worktree: historical inventories and expected reports were read from the restored
archive itself using the recorded execution code, without original working
evidence. Archive integrity covered 8,429 logical files stored in 932
unique blobs (4,246,296 compressed bytes), including the complete 125-file
historical failure inventory. Source checks also matched the 222-file Primary
receipt, 933-file paired receipt and 21 archived public-material files. Public
source equivalence, declared recommendation-provenance redactions, JSON reference
expansion, arithmetic, tracked local links and privacy checks passed. Temporary
restorations were removed; native working originals and absolute preparation
bindings remain intact. Relocated native descriptor readers passed; original
absolute-path preparation commands are not claimed to be portable.

## Historical context and assistance

The first actual V0 attempt, at source
`f49503a3359ddb6ed64c79465fc010143a5b141c`, stopped before an itinerary with
`ClarificationRequired`. Its HTTP 200 interpretation response represented the
exclusive transport clause as unresolved hard semantic text; the then-current
gate returned `unsupported_hard_requirements` for `semantic_4`. Network-disabled
replay of the saved response reproduced that gate. It used one model send,
12,139 tokens, 26.438 native seconds and USD 0.001477615. V1–V3 and Primary did
not run in that attempt. An earlier approval rejection occurred before process
creation and had zero sends. Original failures, approvals, responses, usage,
semantic records and report bytes remain intact in private evidence.

Revision 2 integrated PR #166 without importing unrelated main-worktree work.
Its first offline finalization encountered a 260-character Windows path with
`LongPathsEnabled=0`. The partial output and error evidence were preserved.
A shorter fresh destination then passed native finalization. This packaging
correction changed no system setting, source bytes or live invocation.

External Codex assistance is separate from Planner/evaluator model usage. Fresh
author/reviewer tasks used configured `gpt-6.1-sol/high` with no inherited context
at 01:56:47–02:00:47 and 02:03:17–02:07:02 UTC on 15 October. The independent
occupancy review used the same configuration at 04:17:04–04:18:43 UTC. A
display-only PowerShell timestamp conversion was discarded and original JSON
strings were re-read unchanged. Seven semantic tasks across both revisions include
an excluded historical author exposed to result summaries; its exclusion and a
historical timestamp-packaging correction remain recorded. The researcher
explicitly increased the semantic-task allowance from six to seven for the
additional independent relevance review at 04:48:44–04:50:42 UTC. That reviewer
received the original request, source-only interests and independent venue facts,
with no candidate-stage membership, Planner judgments, itineraries or scores.
Its model/effort settings were inherited and could not be independently verified.

A current-session child configured `gpt-6.1-sol/medium` executed the five bounded
live invocations and reported their actual records. Parent Codex prepared the
packages, checked sources/resources and receipt integrity, and maintained this
report. Genuine partial task/response and provenance records remain private;
full internal transcripts and independent runtime model introspection are
unavailable. Agent review is not human review.

## Acceptance

On 15 October 2026 (Australia/Sydney), the researcher explicitly accepted the
complete case-04 results and stated limitations. Acceptance covers the unchanged
request, revision-2 V0-V3 selections and Primary report bound above, all five
offline native reports, the [indexed public materials](material-index.json) and
their verified private evidence. The explanation of the 275 UNKNOWN relevance
judgments preceded this decision; those outcomes and all other reported
limitations remain unchanged.

This completes automatic case acceptance. Blinded human review is deferred;
these observations are not final research conclusions.

Local integration on 15 October 2026 retained the original history through worker
head `9c8c0d7` on main baseline `5cdc9ab`. Its tracked changes are limited to this
case's 22 material files; the main application, shared rules and other cases are
unchanged. The private archive was transferred separately and passed the
source/relocation checks above. Original case working evidence remains retained.
Publication and Issue lifecycle are tracked in Issue #153, separately from
automatic case acceptance. The existing instruction not to advance case-14
remains in effect.
