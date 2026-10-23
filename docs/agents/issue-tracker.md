# Issue tracker and local planning workflow

GitHub Issues in `rplalala/Dayloom` own live task state,
dependencies, assignments and discussion. [PROJECT.md](../../PROJECT.md) owns
current project scope and authorization; tracked docs own detailed contracts and
acceptance. See the [migration and legacy mapping](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/36#issuecomment-5956795623).

## Specifications and child tickets

Matt's `to-spec` publishes a GitHub spec/parent Issue; `to-tickets` creates its
GitHub child Issues. `triage`, `implement` and `wayfinder` read and update those
Issues. "Publish to the issue tracker" means create/update a GitHub Issue, and
"fetch the relevant ticket" means read that Issue and its comments. A wayfinding
map is a parent Issue holding Notes, Decisions-so-far and Fog; claims use assignment,
and resolved answers belong in the child Issue and parent progress summary.

Optional local drafts may retain a spec and its child-ticket files. Migrated copies
record the GitHub URL and are historical planning aids, never the formal spec owner
or a second live tracker. Local-only files may link to each other. `.scratch/` is
ignored scratch space, not the default output of any publishing skill operation.

Promote accepted requirements, decisions and acceptance evidence into an existing
core design/contract document under docs/, or a dated evidence document under docs/records/.
Use sections/anchors for related tickets instead of duplicating specs across many
files. A GitHub parent Issue maps to the spec; child Issues map to its slices.
Use native sub-issues when the available API supports them; otherwise keep explicit
reciprocal parent/child links and identify that fallback. Preserve dependencies.

## GitHub operations

Use `gh` with an explicit repository argument when authenticated; the connected
GitHub tools are an alternative. Fetch body and relevant comments before updating.
Check existing issues before creation. Use the five roles in
[triage-labels.md](triage-labels.md); readiness and completion never grant scope,
live-run, publication or freeze approval. PRs are not a triage request surface.

Publish only authorized issue work. Keep English bodies self-contained and link
only to accessible published revisions or Issues. Do not link an Issue to a local
file, ignored scratch draft or unpublished commit. During unpublished changes,
describe the new state inline and label older pinned links as historical evidence.
Do not rewrite old pinned URLs to a new path in an old commit.

For a completed legacy task, preserve actual validation and remaining limitations,
map its local spec/child ticket, then close the Issue as completed. Unimplemented
work stays open. Retiring a local tracker does not mean its feature was implemented.
Re-read the remote outcome after every mutation. Native dependencies and issue
numbers/API database IDs are different concepts.

## RTPEval mapping

[Parent #12](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12) owns
Tickets 01-12, mapped respectively to #13-#24. See the
[historical migration acceptance](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12#issuecomment-5956797691)
and [planning record](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12).
Tickets 10-12 and the parent remained open at the original migration checkpoint.
The separately authorized 2026-10-04 engineering delivery published their implementation
and verified all twelve children and the parent closed/completed; see the
[delivery acceptance](https://github.com/rplalala/Reliable-Trip-Plan-Agent/issues/12#issuecomment-5973135724).
Use live Issues for subsequent lifecycle state; completion grants no formal-run or
version-freeze authorization.

## Commit and publication boundary

Local commits within approved scope follow AGENTS.md without repeated permission.
Push, merge, PR creation and branch switching require explicit authorization.
Validate tracked links using the Git index, not merely filesystem existence:
remote documents must not depend on ignored files. Repository-relative links to
tracked assets resolve on GitHub after publication. Local-only evidence paths are
labelled historical identifiers rather than clickable dependencies.
