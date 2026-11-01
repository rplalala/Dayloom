# Model-reference engineering evidence

September–October 2026 failures motivated bounded correction, short references and exact
input provenance. Current contracts are [identity references](../../0001-system-architecture.md#model-identity-references)
and [requirement provenance](../../0002-requirements-evidence.md#input-gate-and-provenance-contract).
Original saved responses remain unchanged; local evidence paths identify historical captures.

## Semantic failure diagnosis

At `339e7e4a4a9eac133f2bdff69217b8b35c6990b4` on 27 September, whole-batch replay isolated
two failure classes. Sydney V1 returned complete identities but promoted ten ordinary food
preferences to unauthorized main exceptions. Sydney V3/Melbourne V1 each corrupted one
canonical ID and its citations despite complete row counts. Exact serializer round trips
ruled out application mapping loss; replacing the bad ID alone still exposed citation error.

The existing citation-only correction could not handle terminal identity/permission errors.
The approved extension used one shared correction across supported reference/authorization
classes, with complete validation before atomic admission. Prompt 4 made explicit exception
permission and required-place bindings visible. Fuzzy identity matching, row-order inference,
partial admission and per-error retry allowances were rejected. The offline gate passed 1,712
with nine skips, plus 72 focused checks. It did not establish live correction reliability.
Evidence: `logs/semantic_reference_network_revalidation_20260927/`.

## Short references instead of another retry

A later Sydney batch repaired an ID on its second attempt but introduced a new citation error.
It stopped at the two-attempt batch ceiling after 49.918s, not because the global time budget
expired. The chosen response was a bijective local place/evidence map, retaining one correction
and global limits rather than adding a third full regeneration.

Offline content-only token substitution reduced accepted 32-row output JSON by 35.9%/37.7%
and input by about 38%, excluding prompt/schema/framing/mapping overhead. This measured copying
burden, not accuracy or billed usage. Valid short references can still be confused.
Evidence: `logs/semantic_contract_revalidation_20260927/`.

## Cross-chain implementation and adapter checks

On 5 October, mappings expanded across primary, Repair, official sources, profiles and Product
introductions. Canonical identity and source ownership were restored before existing checks;
prose/quotes/URLs stayed untouched. A neutral shared helper and JSON-only evaluator packet
preserved the evaluator's planner-free import boundary. The stable full gate passed 2,686
with ten skips.

Six separately selected live adapter samples had no new restoration failure. Review found the
Repair harness bypassing `build_repair_input` and primary omitting `validate_output_sources`;
corrections restored public seams. Later full backend passed 2,705 with ten skips, unlike the
earlier pre-correction gate. These samples did not exercise complete orchestration or prove
semantic judgment accuracy; native identity adoption was still zero at that checkpoint.

## Shared requirement boundary correction

On 15 October, Issue #165 addressed clear inputs failing hard WALK/TRANSIT support, empty pace
representation and paraphrased source quotations. Implementation `0f979a1`, from
`9a834a665de89a709ffb62efa7d5898be807c900`, connected hard modes, exact source endpoints,
pace defaults and independent evaluation. Review corrections checked prompt projection,
replaced coarse token spans with codepoint endpoints and prevented duplicate transport
penalties from nested equivalent quotations. Historical formats retained explicit readers.

| Verification | Observed result |
| --- | --- |
| Broad backend overlapping corrections | 4,196 passed, 17 failed, 16 skipped; not a final-revision green gate |
| Final provider/evaluator selection | 422 passed; six supplementary exact-scope/Unicode/ownership checks passed |
| Corrected CLI/mock selections | 9 soft-quality, 87 generation and 21 opportunity checks passed |
| Bounded launcher retest | Three previously timed-out cases passed with test-only 60s startup bound |
| Final provider classification controls | Both wrapped 401/503 cases passed |

The 17 failures comprised seven obsolete mock shapes, six date-sensitive CLI checks, three
launcher timeouts and one classification anomaly. The first 16 had explicit corrections;
the anomaly did not reproduce on final static source and its original caught cause was not
available. Source mutation during the broad run remained a hypothesis. No final full rerun
was performed. All 478 preserved files, including 388 original case attempt files, matched.

Delivery replayed the eight task commits onto `6b11572c1c2331b61f263727dd7901ba8353752c`;
675 backend/tools blobs matched the reviewed implementation. Delivery reused those verified
checks rather than claiming another run. Case-01/02 public material round-tripped exactly;
case-03/06 post-fix compatibility checks retained their own source bindings. Original failed
responses still reproduce failure under network denial; they were not corrected in place.

## Limits

Strict reference validity establishes ownership, not venue truth or semantic correctness.
Offline sizing and mock gates are not real-model reliability measurements. Historical
operator limits and consumed packages are evidence of those runs, not current defaults.
