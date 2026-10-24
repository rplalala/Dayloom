# Case-04 new-date generation and independent evaluation

## Scope and source binding

The authorized Singapore request covers **25–26 October 2026**, two adults,
SGD 800, a fairly full garden/city/view itinerary and WALK/TRANSIT-only transport.
Four new single invocations used source `4f4d0b5444faa2dbd42cee19bf18bd04e0b79371`
and exact input SHA `11ebfbef8b31ed2f4c1986abb31633e081be2fc0e7804c5111078c68612c90b0`.
The real application reference date was 24 October in Australia/Sydney; the
request passed the date window without a clock override. Runtime policy and
product implementation were unchanged. Pre-existing `.env.example` and
`GLOSSARY.md` edits were excluded from this work.

The [current case report](../../../benchmark/case-04/report.md) owns the detailed
results, resources and acceptance boundary; the [selection](../../../benchmark/case-04/selection.json)
binds exact input, generation and evaluation sources. The
[twelve-case report](../../../benchmark/report.md) owns aggregate results.

## Observed behavior

Primary final scores are **V0 66.6667, V1 50, V2 61, V3 100** under
`rtpeval_daily_density_3`. Their primary-visit counts are respectively 4/4, 5/4,
4/3 and 3/3. V0's Botanic Gardens → National Museum route needs 2,583 seconds
against a 2,100-second scheduled gap; the 483-second deficit exceeds the
300-second tolerance. V2 omits a Sultan Mosque → Garden Rhapsody transfer mode,
leaving route and whole-trip transport-restriction UNKNOWNs. Missing claims
were not repaired during evaluation. Acquisition completed without failed sends;
evidence status remains unresolved because those substantive UNKNOWNs persist.

V3's draft has 6/3 visits and its final has 3/3 after three retained deletions.
The native outcome is `ACCEPTED_COMPLETE`, Rich completion `complete`, with no
blocking findings or unverified return checks. Unsupported diagnostic UNKNOWNs
remain in the validation record. The independent same-run Pair and its continuing
checks are reported separately from Planner completion.

## Execution and independent roles

The user authorized autonomous completion through independent evaluation,
dependent analysis, publication and merge, with final acceptance left to the
researcher. The coordinator bounded the work at USD 40: V0 2, V1 8, V2 10, V3 10,
Primary 6 and Pair 4. Each ran once, sequentially, with zero outer retries.
Observed reference consumption is **USD 8.168798870**.
Original retail reference rates are not account invoices; external Codex costs
remain separate and unavailable. The current case report preserves cumulative
historical price conflicts instead of inventing a complete all-attempt total.

Fresh independent source-only author/reviewer roles bound the requirements,
interests and destination context. A separate claims reviewer checked role/time
and transport declarations before Primary. Venue relevance used independent
official evidence and retained compatible historical decisions with original
provenance; 270 of 336 labels remain UNKNOWN. Actual actor identities and available
configuration metadata are in the case report and source records. Preliminary
contexts exposed to excluded summary/internal fields were discarded and replaced
with fresh reviewers. These agent judgments do not substitute for human acceptance.

## Verification and evidence retention

Read-only retrieval compatibility passed with zero embedding sends. An initial
standalone Windows preflight needed the existing selector event-loop convention;
its subsequent sandbox database timeout disappeared under approved elevation.
No database credentials, permissions or project configuration were changed.

Native intake and semantic readiness passed. Primary and Pair replayed against
their exact saved evidence. All five research tracks passed native source-bound
reconstruction; public verification checks 48 final and 24 paired stages, exact
ranks, 48 selected resource rows, material hashes and V3 completion. No production
code changed, so the delivery uses these data-specific checks rather than repeating
the prior full backend suite. The modified publication verifier passes Ruff.

Private evidence identifier `.scratch/case04-oct25/` retains the immutable captures,
preparations, HTTP journals, receipts, usage, actual independent review records
and offline reconstructions. Native original bytes are separate from LF-normalized
public projection hashes. Current material is pending researcher acceptance;
blinded answers and thesis prose are unchanged.

## Historical context

The [earlier source-bound record](2026-10-24-rich-primary.json) preserves the
24–25 October single-V3/Primary stage. Its original run and receipts remain
unchanged. The [preceding publication](https://github.com/rplalala/Dayloom/tree/4f4d0b5444faa2dbd42cee19bf18bd04e0b79371/benchmark/case-04)
also preserves the same-day completion correction and intermediate offline date
projection. The current selection uses newly generated and independently evaluated
25–26 October outputs; historical acceptance stays attached to its original sources.
