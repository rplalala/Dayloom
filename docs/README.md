# Documentation

Choose the guide for the task:

- [Deploy Dayloom](guides/deployment.md): install, restore data and launch.
- [Develop and configure](guides/development.md): local settings, checks and maintenance.
- [Reproduce experiments](guides/experiments.md): generate outputs and run independent evaluation.
- [Verify findings](guides/verification.md): check retained evidence and report reconstruction.

[PROJECT.md](../PROJECT.md) defines current capability and scope.
[README](../README.md#project-structure) maps the source tree;
[terminology](../GLOSSARY.md) defines domain terms.

## Core designs

| Document | Responsibility |
| --- | --- |
| [0001 System architecture](0001-system-architecture.md) | Layers, versions, request flow and resources |
| [0002 Requirements and evidence](0002-requirements-evidence.md) | Input provenance, semantics, acquisition and qualified supply |
| [0003 Itinerary and transport](0003-itinerary-transport.md) | Roles, time, occupancy, counts and declared populations |
| [0004 Retrieval](0004-retrieval-persistence%28v2v3%29.md) | Corpus identity, persistence, exact ranking and compatibility |
| [0005 Validation and Repair](0005-validation-repair%28v3%29.md) | Permissions, bounded search, adoption and completion |
| [0006 Independent evaluation](0006-independent-evaluation.md) | Scoring, evidence, research tracks and comparison units |
| [0007 Application operations](0007-application-operations.md) | Accounts, tasks, storage, recovery, APIs and media |

## Architecture decisions

- [Version isolation](adr/0001-version-isolation.md)
- [Application-owned transport](adr/0002-transport-ownership.md)
- [Persistent exact retrieval](adr/0003-persistent-exact-retrieval%28v2v3%29.md)
- [Independent evaluation](adr/0004-independent-evaluation.md)

## Detailed technical contracts

RTPEval has five contract owners:
[artifacts/evidence](contracts/0001-evaluation-artifacts.md),
[intake/identity/usage](contracts/0002-intake-identity-usage.md),
[requirements/schedule](contracts/0003-requirement-schedule.md),
[opening/routes](contracts/0004-opening-routes.md) and
[quality/human review/pairs](contracts/0005-quality-human-review.md).
They define current wire formats, policies and replay compatibility.

## Data, results and evidence

| Material | Entry point |
| --- | --- |
| TripWorld sources, processing and recovery | [Dataset README](../data/tripworld/README.md) |
| Twelve accepted case selections and workflow | [Benchmark index](../benchmark/README.md) |
| Automatic results and resource summaries | [Benchmark report](../benchmark/report.md) |
| Human/model blinded rankings and questionnaires | [Blinded results](../benchmark/blinded-results/report.md) |
| Consequential engineering decisions and scoped validation | [Historical records](records/README.md) |
| Original proposal | [Proposal](proposal.md) |

Historical records explain decisions and observed failures; they do not override
current designs. Raw native evidence retains its original source/policy bindings.
