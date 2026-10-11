# Accepted benchmark material

This directory stores accepted, source-linked benchmark candidate bundles. The
producer/user owns case selection; directory placement does not establish a formal
benchmark population, initiate evaluation or certify itinerary quality.

## Admission

Admit a case only after its complete original request, independently authored and
reviewed RequirementSpec, selected V0-V3 results, usage envelopes, provenance and
producer completion declarations pass native intake. Usage may explicitly be
unavailable under the existing contract. Preserve FAIL and UNKNOWN outcomes; material
acceptance is distinct from scoring PASS.

Use the existing [material handoff](../backend/evaluation/README.md#installed-generation-and-material-handoff)
and [artifact contract](../docs/contracts/0001-evaluation-artifacts.md) for schemas,
qualification, source bindings and integrity checks. This directory adds a storage
convention, not another acceptance schema or an automatic admission command.

## Layout

Each case revision is a complete batch-root bundle, with its own accepted
`manifest.json` and all referenced material inside that root:

```text
benchmark/
  <case-id>/
    <revision>/
      manifest.json
      ... referenced request, requirements, results, usage and provenance
```

The referenced subdirectory names are preserved from the finalized material;
readers use manifest references rather than infer files from this example. An accepted
case revision contains one request group and its four selected version runs. Keep case
and run IDs unique when explicitly assembling a later multi-case evaluation batch.

For new material, point `rtpeval batch finalize --directory` at a fresh case revision
directory. For an existing accepted bundle, copy the complete batch root without
changing artifact bytes or relative paths, retain the original evidence, and run
`rtpeval validate` against the copied manifest before admission. Do not move existing
prepared evaluation runs: their bindings include original absolute paths.

Accepted revisions are immutable. Changed input or source material requires a new
revision and validation. Construction drafts, incomplete attempts and unaccepted
material remain outside this directory.

Evaluation evidence, reports, controlled executions and blinded-review answers remain
under explicit fresh directories in `artifacts/`. They are linked to selected inputs;
they do not overwrite accepted benchmark material. Evaluation does not automatically
scan or run every case in this directory.

## Local storage

Case bundles are ignored by Git; only this README and the local ignore rules are
tracked. Keep private prompts and raw provider/model payloads out of commits. Shareable
acceptance summaries belong in the existing `docs/records/` owners. No cases are
admitted merely by creating this directory or by having passed an engineering pilot.
