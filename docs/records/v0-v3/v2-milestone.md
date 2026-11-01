# V2 implementation milestone

The 20 September 2026 checkpoint accepted bounded end-to-end retrieval integration.
It preceded V3 implementation and formal evaluation. [Retrieval design](../../0004-retrieval-persistence%28v2v3%29.md)
owns current behavior; [development evidence](v2-development.md) preserves corpus,
performance and failure diagnoses.

## Accepted scope and observed coverage

The accepted path covered pinned corpus/vectors, exact PostgreSQL retrieval, query embedding,
Google identity/Details resolution, canonical merge, shared supply, primary generation and
Nearby. RAG-only candidates reached scheduling; V1 initialized no RAG and V0 used no tools.
Tokyo cleanup and Sydney ten-day smokes completed. Tokyo forecast 404 was limited coverage;
Sydney exercised K16, 256 baseline route elements, Reviews/Profile and RAG fallback, but also
returned empty/repeated days and unresolved access/time/cost facts.

The cleanup full backend passed 839 of 848 collected with nine skips. Later stable chronological
normalization passed 78 affected tests without rewriting or rerunning Sydney. Sorting preserved
facts/times and did not establish feasibility. This documentation checkpoint ran no new tests.

## Earlier quality-first pair - 2026-09-20

The earlier V2 quality run had 16 RAG Details, fifteen admitted cache-qualified plus 24 ordinary
successes, 39 compared, twelve supplied and eight scheduled, including two RAG-only places.
It used a 160k input guard/16384 output allowance. Reviews/Profile and ten-day K16 were not
covered there; later checks extended those specific paths, not old validation claims.

Corpus Phases 1–5 were accepted separately before runtime. Normal RAG followed initial
Google-only degradation under a selected 60s SQL/180s phase allowance. Storage optimization
remained deferred; the shadow-table proposal was not implemented. Required-identity ambiguity
was outside that normal-path acceptance. See [bounded normal RAG](v2-development.md#bounded-normal-rag-validation).

## Later shared first-draft checkpoint - 2026-09-20

Shared full-range guidance, roles, diagnostics and K20/400-element route support followed with
offline checks. The broad invocation recorded 859 passes, nine skips and two failures;
45 targeted checks passed after correction. It was not retrospectively a green full run.
No live check of that prompt or new freeze followed. Those shared mechanisms were not V3-only.

On 25 September, optional transfers and mixed-mode first-generation transport preserved
V2's independent tools/RAG path without Repair. The [shared evidence](v1-development.md#shared-mixed-transport)
and [historical Product boundary](v3-milestone.md#delivered-mechanism-and-historical-boundary)
identify their scope.

## Limits

Acceptance established mechanism integration, not universal correctness, RAG superiority,
production latency or benchmark completion. Empty/sparse days, repeats, route/opening
conflicts and UNKNOWN visitor access/cost remained possible. Later shared fixes require
their own source checkpoint; historical outputs do not acquire new validation by implication.
