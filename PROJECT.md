# Reliable Trip Plan Agent

Reliable Trip Plan Agent studies how external evidence, retrieval and bounded
validation/Repair affect generated travel itineraries. Dayloom is its traveler-facing
application; RTPEval independently assesses selected planner outputs.

This file defines current scope and capability. [README](README.md) is the user
entry point, [docs](docs/README.md) indexes designs, and GitHub Issues hold
specifications and live task state.

## Architecture and versions

The system is a modular monolith: React, FastAPI, a Python planning backend and
PostgreSQL with pgvector. Product uses the `app` schema; TripWorld retrieval uses
`tripworld` in the same database.

| Version | Mechanism | Independent entry point |
| --- | --- | --- |
| V0 | Shared interpretation, plain generation and estimated transport | `scripts/run_v0.py` |
| V1 | External place, weather, route and supported official evidence; qualified supply and Nearby | `scripts/run_v1.py` |
| V2 | V1 plus retrieval, identity resolution and canonical merge | `scripts/run_v2.py` |
| V3 | V2 plus validation, authorized Repair and re-validation | `scripts/run_v3.py` |

All four remain independently runnable. Product uses V3 through a version-agnostic
public interface. The [architecture](docs/0001-system-architecture.md) defines
shared stages, extension points and resource ownership.

## Planning behavior

Structured trip facts and source-linked user requirements govern interpretation.
Hard obligations, soft interests, pace and transport preferences remain distinct.
Unsupported or ambiguous hard requirements receive explicit feedback; evidence or
resource shortages do not silently weaken a clear request.

V1–V3 acquire and qualify canonical candidates before generation. Provider-owned
names and addresses survive normalization. Primary visits, supporting activities,
free windows, transfers and optional Nearby have separate roles. Unknown opening,
access, price, identity or route facts remain unknown.

V3 edits within application-granted permissions, protecting hard obligations,
fixed time, coverage and source facts. The best publishable result survives later
rejection or exhaustion. Rich completion is assessed per applicable date with
sourced overrides. Internal validation does not establish independent quality.

Detailed rules: [requirements](docs/0002-requirements-evidence.md),
[itinerary/transport](docs/0003-itinerary-transport.md) and
[Repair](docs/0005-validation-repair%28v3%29.md).

## Dayloom application

The lifecycle is account-owned brief/draft → durable task → recoverable preview →
explicit Save or Discard. It includes profile defaults, a mixed draft/trip library,
independent copies, historical import/export and known-input replanning. Guests can
inspect two bundled historical examples. Account images use initials.

Tasks survive browser disconnection; Stop explicitly cancels work. Save is atomic
and idempotent. Imports remain unverified, and copies preserve source trust. Media
uses authorized place bindings or labelled atmosphere imagery with illustration
fallback. [Application operations](docs/0007-application-operations.md) owns the
API, persistence, security and recovery rules.

Local configuration supports database connections, provider credentials and JWT
signing keys. Existing keys are retained; a new local installation generates and
saves a key when absent. Personal settings and secrets are ignored by Git.
Use [deployment](docs/guides/deployment.md) to install and
[development](docs/guides/development.md) for configuration and maintenance.

## Data and independent evaluation

TripWorld is a pinned, deterministically processed metadata corpus with stored
`text-embedding-3-small` vectors. V2/V3 use geographically filtered exact cosine
retrieval, then resolve Google identities. Retrieval relevance does not establish
current operating facts. The [dataset README](data/tripworld/README.md) covers
sources, processing, artifacts and restoration. Large data and private native
experiment evidence are distributed separately.

RTPEval preserves submitted bytes and uses independent evidence. Implemented tracks
cover final quality, resources/costs, V3 draft/final pairs, controlled Repair,
mechanism observations and blinded assessment. Each retains its own population,
policy, uncertainty and source bindings. [Evaluation architecture](docs/0006-independent-evaluation.md)
maps these tracks; [experiments](docs/guides/experiments.md) explains new runs and
[verification](docs/guides/verification.md) explains saved-result checks.

## Research materials and limits

The [benchmark index](benchmark/README.md) identifies the twelve accepted cases and
exact selections. The [automatic report](benchmark/report.md) records mean-score
order V3 > V2 > V1 > V0. The [blinded report](benchmark/blinded-results/report.md)
contains one human and one model assessment of those twelve comparisons. Both rank
V3 first overall, with different second-place preferences. These are descriptive
results for the retained study, not a causal or population-wide guarantee.

Exact replay requires source-bound reports and compatible historical producer code.
A current checkout cannot relabel old receipts or bypass fingerprints. Provider
regeneration may differ from saved evidence/vectors. Reference cost estimates are
not invoices when billing data is unavailable.

Engineering validation covers isolated PostgreSQL, browser workflows, offline
provider fixtures and separately bounded live journeys. [Records](docs/records/README.md)
retain revision-specific results and unresolved coverage. The latest
[application checks](docs/records/frontend/dayloom-product-lifecycle-acceptance.md#latest-regression-corrections-and-limits)
include targeted corrections after a full backend run; the complete suite was not
repeated afterward.

## Scope

Current work covers architecture, implementation, documentation and independently
runnable V0–V3. The twelve-case evaluation and blinded assessment are completed
study materials. New formal experiments, thesis writing and final research
conclusions need explicitly agreed scope. Acceptance implies neither a version
freeze nor public hosting readiness or permission to publish restricted material.

Detailed historical decisions belong to topic records.
