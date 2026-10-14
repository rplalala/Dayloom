# Case 06: Sydney family trip

## Status and request

**Blocked at batch registration, 15 October 2026 Australia/Sydney.** V0-V2
completed their single selected generation attempts and remain selected unchanged.
V3 a1 failed with `TimeoutError`; the authorized replacement a2 completed Planner
generation but failed registration with `Source path escapes collection root`. No accepted
four-version manifest, primary preparation, primary score or opening-access
assessment exists. This is a registration failure, not an evaluated quality UNKNOWN.

[Issue #155](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/155) owns
this case's live state; [parent #151](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/151)
owns the approved first-wave budgets and concurrency. The researcher authorized
the initial steps 1-6 with USD 30 generation and USD 10 primary evaluation, one
attempt per version and zero automatic retries. After a1 failed, the researcher
approved one additional V3 attempt with a USD 12 reference allowance, confirmed
a live slot and explicitly started a2. The USD 40 case and USD 200 batch reference
allowances remain unchanged; the original a1 bill is unknown. All live processes
have ended. No retry or registration repair was performed. Primary evaluation
requires a separate human instruction; case-08/10 remain unstarted. Coordination
now occurs directly with the researcher, without automatic queue or backfill.

The unchanged [original request](../inputs/case-06.json) is a four-day Sydney trip,
15-18 October 2026, for three travelers with a whole-group budget of AUD 2,200.
Two adults and a child enjoy science, nature and outdoor spaces, favor breaks and
less continuous walking, and have a rental car with a preference for driving.

## Semantic preparation and source binding

Different source-only Codex agents authored and reviewed the native requirements
and interest inventory before generation. No named-place, count, exclusion or
fixed-time obligation was stated. Family context, breaks, walking comfort and
driving remain soft preferences; the review adds no age, walking threshold or
rest quota. Science, nature and outdoor spaces remain separate interests.
The reviewed transport status is `unrestricted`, without compulsory `stated_mode`.
Density is `relaxed`, `exact_count=null`, with no dated overrides. Independent
destination context identifies `Australia/Sydney`.

Native external-handoff validation passed against the unchanged input and genuine
author/reviewer files. The semantic sources are prepared and hash-verified; they
have not been attached to an accepted four-version evaluation package. Occupancy
review and primary-package validation were not reached.

| Binding | Value |
| --- | --- |
| Delivered starting commit | `6b11572c1c2331b61f263727dd7901ba8353752c` |
| Generation source commit | `f49503a3359ddb6ed64c79465fc010143a5b141c` |
| Replacement a2 source commit | `2f53f87f32d9ae45fca5c8b3aa6d6d616757ce24`; only this case report differs from the original generation source |
| Original input SHA-256 | `fdd5b2c9c0f80ca220dbed91108058b619c5bd9232363c928bd231f8b976796a` |
| `config/runtime.yaml` SHA-256 | `a6c932272e8d5037ed66fb057e629f8dcff44f3e12117d2dbcb16c8905454058` |
| Reviewed RequirementSpec SHA-256 | `286cb15b1925871dde6bff77cc693b861466cadef58d67023d853beaa2f27266` |
| Reviewed interests SHA-256 | `9734530783049ff5b416ffb6c21b2f2f72001a9781ac8c2a1ae80fb13e8da9d0` |
| Native batch identity | `case-06-primary-20261015-01`, revision `1`, group `case-06` |

Every actual generation dispatch revalidated the complete input window against
`SystemDateProvider('Australia/Sydney')`, returning 2026-10-15. No date was changed
or backdated. Original runs use `case-06-vN-20261015-a1`; the replacement is
`case-06-v3-20261015-a2`, selected in native batch revision `2` with the original
V0-V2 run identities and bindings.

## Generation and observed consumption

| Version | Actual attempts | Outcome | Model calls | Google sends | Observed tokens | Elapsed seconds | Reference USD |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| V0 | 1 | Completed | 2 | 0 | 21,232 | 132.437 | 0.00573635 |
| V1 | 1 | Completed | 11 | 50 | 67,857 | 139.203 | 2.07843713 |
| V2 | 1 | Completed | 12 | 66 | 73,237 | 150.453 | 2.44711137 |
| V3 a1 | 1 | Failed: `TimeoutError` | 1 | 0 | Unavailable | 1639.141 | Unavailable |
| V3 a2 | 1 additional | Planner completed; registration failed | 12 | 75 | 71,837 | 151.532 | 2.627493645 |

V2's model count includes one `text-embedding-3-small` call; the other model calls
use the observed `gpt-6-luna` deployment. V1/V2 passive candidate capture is
available. V2's producer declares retrieval completion while preserving its
`partial` retrieval observation. No candidate or Repair process analysis was run.

V0-V2 have complete reported usage and no unpriced events. Their reference subtotal
is **USD 4.53128485**, with **162,326 observed tokens**. This is not the complete
case cost or token total: V3 a1 has one uncompleted Foundry HTTP send, absent provider
usage and two unpriced cost events. Its account and reference totals are null.
The a2 model count includes one embedding call; its 88 HTTP sends include 76 tool
sends (75 Google and one weather send). Its 71,837 tokens comprise 58,181 input
and 13,656 output tokens, with no missing usage fields, incomplete HTTP sends or
unpriced cost events. The known V0-V2 plus a2 reference subtotal is
**USD 7.158778495**, with **234,163 observed tokens**. The failed a1 remains outside
those known subtotals. Actual account invoices and external Codex tokens/billing remain unavailable.
Generation prices retain the native 2026-10-08 reference basis; the coordinator
rechecked public references on 2026-10-15. Foundry prices are the declared OpenAI
retail proxy, excluding credits, free quotas, discounts and tax.

## V3 attempts and evaluation gate

Before a2, a private standard-library process guard passed six offline checks,
including a three-second timeout ending after 3.016 seconds. The real CLI prepare
check completed without provider sends; 508 V0-V2 dependency files passed native
reuse validation. The guard SHA-256 is
`c4aa39c0171460a6af462793c694aa0be7943368fca060c632fd87f04e6810bd`.
The replacement retained the existing token and Repair limits, used a 600-second
outer process deadline, and allowed no automatic retry. This guard bounds process
execution rather than monetary billing.

The a2 guard started at `2026-10-14T21:19:12.711096+00:00` and ended at
`2026-10-14T21:22:04.594960+00:00`, with the owned subprocess ended and exit code
`2`. Outer elapsed time was 171.891 seconds; native selected-invocation-through-
cleanup time was 151.532 seconds. The deadline was not reached. Planner exit code
was `0`, with result, provenance and usage retained. Its producer
declares generation, retrieval and validation completed, while preserving a
`partial` retrieval observation. Repair is `not_applicable` with
`no_authorized_targets`, and Repair model calls are zero. These are producer
observations rather than evaluated quality judgments.

Registration then failed with `Source path escapes collection root`; no staging
directory or qualified four-version package was created. Offline diagnosis on
15 October reproduced the exact failure twice from the saved collection, with
network access disabled and no source writes. The parent preparation helper had
embedded complete native V0-V2 completion dictionaries in the new root-level
selection without rebinding their capture-relative references. Recursion followed
a2 provenance, a2 producer completion, its operator selection snapshot, then
`groups[0].selected_runs.v0.completion.operator_selection_ref`. Its unchanged path,
`../../generation-selection-378b0eb726694dfbb287f3ffac922169.json`, was resolved
against `work/` instead of the original `primary-20261015-01/captures/v0/` owner.
The resulting target escaped the bounded root; the containment check correctly
rejected it. In the native owner the target exists and its hash matches. V1/V2
carry the same copied-reference pattern. No link anomaly was found; enlarging the
root points to a nonexistent wrong target rather than repairing ownership.

The earlier offline preparation checked V0-V2 directly and a pending V3 slot,
without exercising the completed V3 provenance-to-selection dependency chain.
Top-level completion qualification checks metadata but does not traverse those
inline reference fields; the new chain exposed the preparation defect only after
generation. Existing source-bound reuse tests use reference-free fixture completion
metadata and do not cover this pattern.

A diagnostic copy of the collector, executed only in memory with native-owner
context for embedded declarations, validated 809 dependency files and completed
all four producer qualification checks. The embedded V0-V2 declarations matched
the original native completion dictionaries. True root escapes and dependency hash
mismatches remained rejected. This is a feasibility probe, not an installed fix,
staging package or evaluator qualification. Original files, a2 result/usage and
failed selection/collection bytes remain unchanged.

The proposed repair normalizes future selections and defines verified native-origin
handling for preserved legacy snapshots, retaining containment and exact-byte hash
checks. Shared collector/generator contracts and regression tests require a separately
approved implementation scope. After that repair, a fresh offline collection can
reuse the existing a2 capture and original V0-V2; the failed registration remains
historical evidence. No application change, re-registration, paid retry or primary
call followed this diagnosis.

### Original a1 failure

V3 preparation was recorded at `2026-10-14T19:46:00.635867+00:00`; producer failure
completion was recorded at `2026-10-14T20:13:20.615575+00:00`. The native
`selected_invocation_through_cleanup` elapsed time of 1639.141 seconds exceeds the
approved 600-second total. The execution child reported that a requested
40-second tool wait blocked for approximately 1632 seconds and returned no stdout;
its next poll received exit 1. These are retained observations. The cause and
which portion of the interval consumed the excess time have not been diagnosed.

Only one model call and one incomplete model HTTP send were observed in V3,
both in the native `requirements` stage;
Google, embedding and Repair sends were zero. No provider tokens were returned.
The producer declares generation, retrieval, validation and Repair `failed`.
There is no result, provenance or draft/final pair. Zero Repair calls here does
not establish a successful no-Repair outcome.

### Evaluation gate

The original a1 registration remains `blocked`; a2 registration is `failed` despite
its completed Planner output. Therefore native four-final intake,
independent evidence acquisition, common-dimension scores, density deductions,
FAIL/UNKNOWN quality findings and primary replay are **not evaluated** for every
version. Reviewed density policy is preparation, not a computed deduction.
The primary evaluator has zero attempts and zero sends. No partial score or
replacement result was fabricated. The separately authorized a2 is the only
additional attempt; no automatic generation retry or consumed-package restart occurred.

## Evidence and actual AI assistance

The preserved private worktree is
`C:\Users\70522\.codex\worktrees\dae0\Reliable-Trip-Plan-Agent`.
Its case-relative evidence root is
`benchmark/scratch/case-06/work/primary-20261015-01/`.
These paths identify retained private evidence, not public download links.
It contains original inputs/configuration snapshots, semantic drafts/finals and
real execution/partial-transcript records, immutable selections, V0-V2
result/usage/provenance/completion and passive captures, V3 failure/usage/completion
and trace, and original staging/registration dependencies. The replacement's
private root is `benchmark/scratch/case-06/work/v3-replacement-prep-20261015-01/`,
containing offline preparation, a2 capture and external guard evidence. After a2,
all 1,932 original files and their byte hashes remained unchanged. No cleanup,
relocation or compact archive replay was performed.

| Evidence | Exact original SHA-256 |
| --- | --- |
| V0 result | `326246140a2ca791d6bd73433a606c80cc1eccce354e85ea9a2d36fc814c5942` |
| V1 result | `8e61f4d5aceb0188c5252353c5ddb8cda353ec822b9919fd793592e71d398fc6` |
| V2 result | `0c22b9a3be6d5a09d7ac1a9794363df39f5e7a05c066c10ad0930ce19c6ac962` |
| V3 `failure.json` | `ee787e1b44f8e25d67510a0d5217328cbfa78602c505f6d59e3aabf0e9e965dd` |
| V3 `usage.json` | `d3c7f36ed32e93e59f67166a0c4d311697800bfd44cdf634451ab74c0a22fb41` |
| V3 producer completion | `9d60f182b74220c93b4113b58d76465f43bb5b772fe44603db12b670c92fe214` |
| V3 a2 result | `23146d0b67b2e81f6010cfcbe2ce643083899671b2a51bdb7189d57d4de07a1e` |
| V3 a2 usage | `7729992af42c09ff39eb59948e851e9a3606987037d0bd547c86f76ae540f365` |

| Work | Actual actor/configuration | Retained scope and limitations |
| --- | --- | --- |
| Requirements/interests/transport/density/time authoring | `/root/case06_author`, selected `gpt-6.1-sol/high`, fresh context | Complete original request and current contracts; actual draft and execution record retained. A current index exposed case-01 acceptance status without quality/results; this limited exposure is disclosed. |
| Independent semantic review | `/root/case06_reviewer`, selected `gpt-6.1-sol/high`, fresh context | Same complete original request and exact author draft; native finals and genuine review record retained. No itinerary, score or mechanism context. |
| Prepared live generation commands | `/root/case06_execution`, selected `gpt-6.1-sol/medium` | Same current-session child executed sequential commands, retained original outcomes and reported consumption/failure. |
| Authorized V3 replacement execution | `/root/case06_a2_execution`, selected `gpt-6.1-sol/medium`, fresh context | Executed the frozen guarded command once, inspected bindings and consumption, and stopped at registration failure. Terminal observations and a derived parent assessment are retained; complete transcript and external token/billing data are unavailable. |
| Orchestration and documentation | Parent Codex agent | Scope/source/date/environment gates, native handoff checks, command preparation, receipt inspection and this report; no shared implementation changes. |
| Human decisions | Researcher | Approved initial scope/budgets, then V3 a2 with USD 12 reference allowance and a confirmed live slot; primary evaluation remains separately paused. No case acceptance or human quality rating. |

Author/reviewer start timestamps are their earliest observed clock samples after
initial reading, not verified dispatch times. Their partial authentic messages
are retained; complete session exports, exact external-agent tokens and bills are
unavailable. Agent review does not constitute human review.

Environment preparation found a sandbox DB connection timeout; the same native
query-only compatibility check passed outside the sandbox with zero embedding
sends. The installed `rtpeval.exe` trampoline could not canonicalize its path;
the same local locked Python environment invoked `backend.cli.rtpeval.main`
successfully. A V2 approval rejection occurred before process creation and any
generation attempt. Static inspection verified that `.env.tripworld` supplies only
DB authentication, embedding sends bounded query text, and existing Google/Foundry
flows use venue fields/normalized evidence without environment-file contents.
Approval then allowed the identical command. This did not retry a provider request.
The initial coordinator message rejection was resolved by direct human messaging
authorization. No credentials or shared runtime policy were changed.
