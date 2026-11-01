# Complete-baseline Docker local acceptance

On 2 November 2026, the unpublished `0.1.0-local` deployment archive was installed
through its real Bash/Compose entry into fresh, independently owned test storage.
Public Release downloads and anonymous GHCR pulls remain unobserved and require
separate publication authorization under [#255](https://github.com/rplalala/Dayloom/issues/255)
and [#247](https://github.com/rplalala/Dayloom/issues/247).
Current commands belong to the [deployment guide](../../../deploy/README.md).

## Artifact identity and build context

| Binding | Observed identity |
| --- | --- |
| Runtime/image revision | `ad2860a9b819f43f152a421c1f3189b7c8769317` |
| App image | `dayloom-app@sha256:9e0f679e0c7c157b318e842b24eb6271c4d39d34ba19017148446fe011b12d85` |
| Baseline tools/data image | `dayloom-baseline@sha256:01de2b57359654a7f8705c228c9308e06e64e59df64d61184d677c5529e5f629` |
| Baseline version | `baseline-20261102` |
| Baseline ID | `9f09388c5bb4bd316463b8ea927bb1cf69803d596e694b30dd9bb11cb05f7fbe` |
| Factory snapshot source | `79301aa11ffbbbdbe03a076572dfe3b7ac3c11ed`, captured `2026-11-01T17:19:05.095505+00:00` |
| Archive | `dayloom-0.1.0-local-linux-amd64.tar.gz` |
| Archive SHA256 | `3ee1d8f7851f346e70c0902f0b9fd998c12a148b4139f5959ba18003449f32f4` |
| Schema fingerprint | `c28d2021bd45802e9d466331a68067123705862aab520b0ec04466c169b7a39d` |

The images contain the runtime at the listed revision plus one uncommitted,
non-runtime wording correction in `deploy/release/publishing.md`, clarifying the
publication/anonymous-download order and installed-instance upgrade instructions.
That file enters both images through their existing `COPY deploy` rules, although
it is not an input to the four-file archive renderer. The acceptance harness and
this record were developed afterward and do not change the tested runtime or
archive bytes. These are local repository digests, not published GHCR references.
A future public release must build from the final clean committed revision and
complete the separate public retrieval/fresh-install acceptance.

Both images were rebuilt after the registration-gap correction. The same existing
factory snapshot was supplied as a named build context; the final rebuild reused
its cached content and transferred only 475 bytes of context metadata. No second
factory export was made. One concurrent app export encountered a Docker parent
snapshot unpack error; the identical app build succeeded when retried serially,
without pruning caches, changing configuration or restarting the source service.

## Complete baseline and Product behavior

The retained archive contains exactly four regular files: `compose.yaml`,
`.env.example`, `start.sh` and `README.md`. Its checksum sidecar verifies both the
archive and each extracted file. Bash ran noninteractively from a different
working directory; no source checkout, host dataset mount or host Python/Node
runtime was used by the installer. Images were already cached locally. The test
project used `dayloom_full_acceptance_test` and independent volumes, replacing only
the explicitly identified earlier disposable acceptance project.

Fresh startup generated independent database, signing and management identities,
retained editable instance configuration and allowed `/config` while business
requests returned `503 local_setup_required`. The management password was emitted
only to the explicit bootstrap caller and was not retained in the acceptance
record. It remained separate from the approved Product test admin.

Before test-owned writes, all 16 restored table counts/content fingerprints,
schema/extension identity and migration records equalled the approved manifest.
This includes the original password hash, owner IDs, related Product rows and full
persisted media metadata. The inventory contained 1 account, 4 saved trips,
7 previews, 6 tasks, 69 trip activities, 44 Nearby rows, 39 transfers, 22 weather
rows, 647,057 corpus entities and 577,011 stored vectors. Ten saved-vector Top-K
rows retained their exact entity order and cosine scores within `1e-12`; no new
embeddings were generated.

The real configuration page saved controlled provider values and displayed the
restart requirement. Restart applied them while keeping provider fields editable.
The actual HTTP boundary rejected an incorrect Host, Origin and missing CSRF
token. Default admin login exposed the original four saved trips; a new draft and
test-owned account were created without planning. The stdin-only test harness
replaced external media HTTP transport inside the running production image, with
no test adapter or bypass installed in that image. Forty-eight persisted place
slots were read with zero acquisition requests. Refreshing one selected slot sent
exactly two controlled Google requests using the destination instance key, kept
other returned slots unchanged and reused a repeated refresh version. Another
account received `404` for the original resource.

A real Chromium browser opened the library and a baseline itinerary. All 19
external image requests were fulfilled with a tiny local PNG, and there were no
other external browser requests. A test-only Compose overlay blocked backend
provider DNS/known destinations and cleared proxy settings. No API-check,
planning, paid provider call or request to an original photo URL was performed.

Stop/start, forced app recreation and starting the app before a delayed database
preserved the receipt and complete retained Product state, including new content,
historical tasks and refreshed media. Signing, database/provider configuration and
the installed baseline identity were unchanged. Harness-only corrections aligned
its initial CSRF status/library-kind assumptions and TestClient URL construction
with existing public contracts; affected stages were rerun against the same
verified installation without changing production code or repeating restoration.

## Recovery protections and operational recovery

The integrated controlled PostgreSQL/CLI evidence covers transactional restore
interruption, the committed-restore/registration gap, concurrent initialization,
corrupt/checksum/sidecar mismatches, unknown nonempty targets and migration
compatibility. The preliminary complete-baseline run exposed an unchanged SQL
migration whose stored digest used CRLF. Startup now accepts exact LF/CRLF forms
without rewriting the stored migration hash or timestamps, while substantive SQL
changes and unknown future migrations still fail closed.

Review also reproduced a registration gap incorrectly accepting an extra standalone
ENUM that the v1 fingerprint did not represent. The correction admits only the
catalog object scope supported by the existing manifest before unregistered
restore/recovery. Controlled tests cover ENUM/domain/range/event-trigger and other
unsupported additions; an already registered installation still permits later user
data. The real baseline passed that admission without changing its ID or exporting
another snapshot. The correction's 29 real PostgreSQL/CLI checks and six Windows
CLI checks passed. The earlier controlled upgrade fixture also exercised a pending
migration exactly once, repeat upgrade, incompatible resources, old-image refusal
and independent recovery with later account/draft/trip/preview/task/media data.

The final full-data archive's supported upgrade command reused the final immutable
app reference, created one consistent private operational backup and preserved the
installed baseline and complete Product state. The backup included its receipt,
new account/draft/refreshed media and private configuration. After checksum
verification and successful candidate preflight/startup, the original test project
and volumes were removed before restoring that same backup into a fresh project;
two complete test databases were never run concurrently. Restore verified the full
database inventory and receipt. Subsequent HTTP checks passed default admin login
and retrieval of the new draft; Product state, signing/database/provider identity
and management-file hashes matched the source test installation. Forty-eight
restored place slots again required zero controlled acquisitions. The pending
migration transition was exercised by the separate controlled fixture described
above, rather than invented for the complete approved dataset.

## Measurements and limits

| Measurement | Observation |
| --- | --- |
| Factory custom-format dump | 4,434,195,118 bytes |
| App `docker image inspect.Size` | 250,748,167 bytes |
| Baseline `docker image inspect.Size` | 4,605,053,520 bytes |
| Four-file gzip archive | 10,440 bytes |
| Private operational backup dump | 4,434,198,051 bytes |
| Fresh install to live setup listener | 318.55 seconds |
| Additional complete inventory and Top-K verification | 29.73 seconds |
| Full backup, verification and compatible app-only upgrade | 913.41 seconds |
| Fresh operational restore, identity/content checks and app startup | 608.50 seconds |
| Sampled initializer Docker displayed memory / cgroup memory | 2,277,406,408 / 3,359,227,904 bytes |
| Sampled PostgreSQL Docker displayed memory / cgroup memory | 5,213,016,555 / 8,576,434,176 bytes |
| Sampled app Docker displayed memory / cgroup memory | 147,744,358 / 217,251,840 bytes |

The observed engine was Docker Desktop 28.3.2, Linux x86_64 on a Windows host,
with 8 CPUs and 16,771,137,536 bytes of engine memory. The source database remained
running separately on the same engine. Container samples were scoped to the test
project and taken approximately every three seconds; separate maxima need not be
simultaneous. `memory.current` includes charged page cache, unlike Docker's displayed
working set. These are observations, not minimum-memory or sizing guarantees.
`inspect.Size` is the reported image metadata metric, not a guaranteed registry
transfer size or VM disk allocation. Budget disk space separately for cached
images, the restored database and a private operational backup. Network download
latency, other platforms and lower resource limits were not measured.
The operational backup was written to and restored directly from a Windows host
bind mount. The restore timing precedes its additional read-only media probe.

Bounded input/resource/image metadata checks passed, and the app filesystem omitted
private configuration, source Git metadata, tests and host dumps/parquet inputs.
Both image histories had zero matches for common private credential assignments;
ordinary app logs contained none of five generated/configured private values.
Original provenance and example-media notices remained present. The baseline
notice ZIP contained 25 entries with no private configuration filenames or common
credential-pattern matches. These checks are bounded inspections, not an exhaustive
secret audit; the approved Product admin and full baseline content are intentional.

Host/configuration and independent V0–V3 compatibility remain tied to the existing
focused regressions. All four independent runner `--help` commands passed import
and argument parsing; no new complete online V0–V3 journey or broad backend suite
was run. This is deployment acceptance, not a benchmark or research conclusion.
The acceptance entry's two disposable-target guards and four existing container
configuration regressions passed together; changed-file Ruff, diff checks and
changed Markdown local references also passed. The target guard first failed for
the missing entry, then passed after implementation.

The reusable opt-in entry is
`python -m backend.tests.deployment.archive_acceptance --help`; ordinary pytest
runs only its disposable-target guards. Safe local evidence identifiers are
`t8-runtime/result.json`, `source-baseline-protection.json`,
`notice-inspection-result.json`, `independent-cli-result.json` and the T1–T7
handoffs under the private shared work area. They are historical identifiers,
not installation dependencies or public download links.

After verification, both disposable test projects and their containers, networks
and volumes were absent. Test-owned generated configuration and the private
operational backup were deleted after exact target checks. The single approved
factory snapshot, final images/archive/checksum and sanitized results were retained;
the original source PostgreSQL service was never modified, stopped or deleted by
this acceptance.
The final SELECT-only source audit compared all 11 Product table digests with the
pre-export evidence and found them unchanged. Source TripWorld access was limited
to the original read-only export and saved-vector query; the final source-content
audit specifically covers those 11 Product tables. Its safe local evidence
identifier is `source-final.json`.
