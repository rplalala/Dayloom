# Controlled release preparation

Deployment sources live in `deploy/`: the four-file consumer entry is at the top
level, Docker build/startup code is in `docker/`, and baseline, maintenance and
release tools are in `release/`. Platform workflow declarations remain in
`.github/workflows/`. The existing host development Compose entry is independent.

## Release identity and checks

An archive is named `dayloom-VERSION-linux-amd64.tar.gz`; its separately distributed
`.sha256` manifest covers the archive and each of its four regular files:
`compose.yaml`, `.env.example`, `start.sh` and `README.md`. Generated instance
configuration, source, dumps, provider keys and registry authentication are absent.
The configuration template contains public release metadata binding the exact
semantic version, app source commit, app/baseline image digests, baseline identity,
database schema fingerprint and both retrieval sidecar hashes. Packaging inspects
cached immutable images and copies only their small metadata files to check these
identities. A mismatched application resource, baseline, revision, version or
platform is rejected. First installation rejects public overrides that disagree
with the archive; existing instances retain their installed baseline through the
maintenance commands. Application and baseline versioning remain independent.

The target platform is Linux amd64. Other architectures have no acceptance claim.
The approved baseline dump measured 4,434,195,118 bytes; the first public baseline
image measured 4,605,052,812 bytes. Package build JSON reports actual archive and selected
image sizes for each build. These are stored image sizes, not compressed transfer
sizes or measured minimum memory/disk limits; allow working room for image layers,
the restored database and private backups.

## Initial baseline bootstrap

Create and verify the baseline using [baseline operations](README.md). The artifact
must be an explicit reviewed local directory containing notices and the approved
Product test administrator hash. That application account is intentionally
retained; infrastructure roles, database-role passwords, provider keys and local
configuration are excluded. Review custom notices before export: checksum
verification establishes integrity, not permission to publish their contents.
The application image retains the TripWorld README and bundled example provenance.

Use a clean checkout of the approved release source, PostgreSQL 17 tools and the
maintainer Python environment. This build-only command verifies the explicit
artifact and builds the large image locally without discovering any database:

```bash
python -m deploy.release.bootstrap --artifact /private/verified-baseline \
  --version baseline-20261102 --source-revision REVIEWED_COMMIT
```

It prints the prospective `docker push` command but never executes it. Only after
separate publication authorization, authenticate to GHCR with a maintainer package
write credential through standard input, push the exact version once, record its
registry digest, associate the package with this repository and set its package
visibility to public. Do not place registry credentials in build arguments,
notices, files in the build context or the user archive. The OCI source label
associates the image with the repository. Verify anonymous pulling separately.

The 4.43 GB dump exceeds GitHub's 2 GiB limit for one Release asset. It is therefore
not uploaded as a Release asset or transferred through the public workflow. The
local bootstrap is the initial large-data path; subsequent application CI reuses
its pinned existing baseline image. No self-hosted runner, new storage service or
connection to an author's live database is assumed.

## Explicit application resources

Prepare a small `tar.gz` with exactly these four regular files, with paths relative
to its root and no directory entries or symlinks:

- `.cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790`
- `data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4`
- `data/tripworld/artifacts/retrieval_entities.parquet.manifest.json`
- `data/tripworld/reports/phase5_embedding_run.json`

Keep the tokenizer files from the verified offline resource build and the two
sidecars from the selected baseline. Record the archive SHA256 independently.
An explicit HTTPS artifact URL plus that checksum is the manual workflow input;
no database dump or author configuration is needed. The artifact may be a small
maintainer asset; it is separate from the four-file consumer archive.

```bash
python -m deploy.release.package resources --archive resources.tar.gz \
  --sha256 VERIFIED_SHA256 --output /new/build-resources
python -m deploy.release.package check-inputs \
  --resources /new/build-resources \
  --baseline-image ghcr.io/rplalala/dayloom-baseline@sha256:BASELINE_DIGEST
```

Staging rejects additional files, links, traversal paths and oversized resource
entries before writing output. Input checks require the Docker context's explicit
exclusions, scan tracked application inputs for common embedded credential forms,
and compare sidecars with the selected baseline. This bounded check complements
review of the clean checkout and Docker build checks; it is not an exhaustive
secret detector. Runtime instance secrets are generated only after extraction.

## Application release workflow

`dayloom-release.yml` is manual-only. Supply the reviewed 40-character source
commit, an exact app version without `v`, the existing immutable GHCR baseline
reference and the explicit resource archive URL/SHA256. The `prepare` job has only
repository read access and builds locally with no publication. Preparation uses
no registry, provider or database secret. It validates Docker build declarations
and uses the verified named resource context. OCI revision/version labels are
added after expensive runtime layers so metadata changes reuse dependency/data
caches.

`publish=true` additionally requests a separate job in the `dayloom-publication`
environment. Configure required maintainers on that environment before use.
Publication needs explicit human authorization; do not trigger this workflow just
to validate its declaration. Its `GITHUB_TOKEN` is scoped to package and repository
writes, is passed only to Docker login and GitHub CLI, and is never a build input.
Actions are pinned to reviewed commits. The job refuses an existing app version,
pushes an app image with SBOM/provenance attestations, pulls its digest, rechecks
resource/label compatibility, creates the deployment archive and creates a draft
GitHub Release containing only the archive and checksum sidecar. Build arguments
are public source/version identifiers; Docker provenance may expose them.

Package visibility needs maintainer configuration: first publication can remain
private even for a public repository. Before publishing the draft Release, verify
anonymous pulls of its exact GHCR image digests and complete local cold-install
acceptance. After separate authorization to publish the Release, verify anonymous
curl retrieval of the exact-version archive and checksum, then install freshly
from those retrieved artifacts. Public-distribution acceptance remains pending
until that entire path passes; a preparation build or draft asset does not prove
anonymous availability. The workflow never rebuilds or exports the baseline,
calls paid providers, or loads an author's runtime configuration.

## Local package verification

Build the app with `SOURCE_REVISION=REVIEWED_COMMIT` and `APP_VERSION=VERSION`.
Pull the selected immutable app and baseline images before rendering:

```bash
python -m deploy.release.package build --version 0.1.0 \
  --source-revision REVIEWED_COMMIT \
  --app-image ghcr.io/rplalala/dayloom-app@sha256:APP_DIGEST \
  --baseline-image ghcr.io/rplalala/dayloom-baseline@sha256:BASELINE_DIGEST \
  --baseline-id BASELINE_ID --output /new/release
python -m deploy.release.package verify \
  /new/release/dayloom-0.1.0-linux-amd64.tar.gz
```

Existing output files are never overwritten. Identical source templates and
identities produce byte-identical archives. `--allow-local-images` permits cached
local repository digests for controlled unpublished acceptance and omits the
public version/provenance label requirements; the app commit label, digest,
platform and resource checks remain mandatory. Do not distribute those local
references as a public release.

The rendered README includes curl commands targeting its exact Release tag and
asset names, checksum checks before/after extraction and maintenance instructions.
Use the target release's immutable application reference with the installed
bundle's upgrade command, and retain the target release metadata with the private
backup. Baseline replacement requires a separate explicit recovery or migration
decision; ordinary application updates retain the installed identity.

Primary references: [GitHub image publication](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images),
[Release asset limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases),
[Container registry visibility](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[Docker named contexts](https://docs.docker.com/build/ci/github-actions/named-contexts/)
and [build attestations](https://docs.docker.com/build/ci/github-actions/attestations/).
