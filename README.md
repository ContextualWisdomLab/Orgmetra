# Orgmetra

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ContextualWisdomLab/Orgmetra)

**Evidence-centered HRIS and HCM for the full employment lifecycle.**

Orgmetra connects job architecture, recruiting evidence, employment records, performance outcomes, and validation evidence without collapsing them into one opaque HR record. It is designed for teams that need HR decisions to remain explainable over time: what the job required, what evidence informed a decision, what happened afterward, and which system owns each fact.

## Why Orgmetra

Traditional HR systems often split job analysis, recruiting, assessment, employment records, performance management, compensation, and people analytics into disconnected workflows. Orgmetra's product boundary is built around preserving the evidence and time semantics that make those workflows auditable and scientifically useful.

| Need | What Orgmetra provides |
| --- | --- |
| HR source of truth | Distinct Person, Employment, Organization, Job, Position, Assignment, candidate-worker, performance, and validation records |
| Time-aware HR facts | Separate business-effective time and system-recorded time |
| Evidence-backed decisions | Explicit evidence and actor context for governed selection and talent workflows |
| Privacy without unusable masking | Purpose-bound authorization, least privilege, encryption, retention, and audit |
| Scientific validation | Predictor, criterion, sample, and policy-version evidence without replacing psychometric/statistical kernels |
| Ecosystem integration | Versioned API, event, package, and adapter boundaries instead of cross-service application-table access |

## Product loop

```text
Job evidence
  -> Task / FJA / KSAO model
  -> SME-approved job profile
  -> Candidate evidence
  -> Structured assessment and interview
  -> Evidence-backed selection decision
  -> Employment / position / assignment
  -> Longitudinal performance outcomes
  -> Validation study
  -> Revised job and selection policy
```

## Core bounded contexts

- People and Employment
- Organization, Job, Position, and Assignment
- Talent acquisition and candidate-worker linkage
- Performance and criterion observations
- Workforce validation and decision evidence
- Audit, provenance, and purpose-bound authorization
- CWL integration hub

## Start with the repository baseline

The root validation path is dependency-light and matches the current Foundation CI toolchain: Node.js 24 and Python 3.14.

```bash
npm ci
npm run validate
```

`npm run validate` checks the repository manifest, foundation contract, OpenAPI structure, and dispatcher inventory. Product packages and PostgreSQL contracts have their own focused test paths; use the applicable package/workflow rather than treating the root validation command as proof of every subsystem.

For the current executable verification contract, see [Foundation CI](.github/workflows/foundation-ci.yml) and [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md).

## Architecture and integration

Orgmetra is intentionally federated. Specialist ContextualWisdomLab products stay independently deployable and integrate through explicit versioned boundaries.

```text
                        ┌──────────────────┐
                        │     Orgmetra     │
                        │ HRIS / HCM truth │
                        └────────┬─────────┘
                                 │
                 versioned APIs / events / packages / adapters
                                 │
       ┌───────────────┬─────────┴──────────┬────────────────┐
       ▼               ▼                    ▼                ▼
   identity       psychometrics        orchestration     data / docs /
    boundary          kernels             boundary        integration
```

Integration maturity is evidence-bound. `implemented_on_protected_main` means the Orgmetra-side boundary is shipped on protected `develop`; `accepted_architecture` means the boundary and contract shape are accepted but are not a shipped end-to-end integration; `planned` means no shipped integration should be inferred.

| External product boundary | Orgmetra use | Current maturity |
| --- | --- | --- |
| **Keyverse** | Identity, OIDC, SCIM, federation, and purpose-bound authorization | `implemented_on_protected_main` |
| **Psychometrics Commons** | Immutable assessment response/result snapshots | `accepted_architecture` |
| **fast-mlsirm** | Psychometric numerical kernels and governed validation-result contract | `accepted_architecture` |
| **Naruon** | Customer-owned communication and calendar integration | `planned` |
| **TEPP** | Temporal, event, multilevel, and multiple-membership evidence | `planned` |
| **Semantic Data Portal / OriginWeave / LineageWeave** | Semantic, source, and lineage evidence adapters | `planned` |
| **Contextual Orchestrator** | Draft-evidence model orchestration; never employment-decision authority | `planned` |
| **MHTML ETL Gateway / mightyETL** | Governed migration and CDC | `planned` |

The detailed evidence, pinned revisions, and required integration proof are authoritative in [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md). Orgmetra does not directly query another product's application tables, and an integration does not transfer the other product's authority into Orgmetra.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the code-current architecture boundary.

## Non-negotiable contracts

1. `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, and `assignment_record` are separate concepts.
2. Effective time and system-recorded time are preserved independently.
3. Database objects are normalized to 3NF and use descriptive two-or-more-word `snake_case` names.
4. Public identifiers are opaque; credentials are never HR person identifiers.
5. PII required for authorized HR work remains usable. Protection is achieved with purpose-bound authorization, least privilege, encryption, retention, and audit rather than indiscriminate masking.
6. LLM output is draft evidence, never an autonomous high-impact employment decision.
7. Inferred lineage is not authoritative audit history.
8. No cross-service application-table access.

## Current product status

Protected `develop` is the shipped repository authority. Treat a capability as shipped only when its current traceability evidence is marked `implemented_on_protected_main`; PRD requirements, accepted architecture, and `implemented_on_active_pr` rows are not protected-branch capability evidence.

Open pull requests may contain additional candidate behavior. Treat those changes as active-PR truth only until they integrate into protected `develop`; use [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md) as the maturity authority and do not infer a shipped capability from PRD scope or a PR description.

The repository does not claim certification, customer deployment, release maturity, benchmark leadership, or autonomous employment-decision authority unless separate current evidence explicitly supports such a claim.

## Documentation map

| Topic | Source |
| --- | --- |
| Product requirements | [`docs/PRD.md`](docs/PRD.md) |
| Technical requirements | [`docs/TRD.md`](docs/TRD.md) |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| User stories | [`docs/USER_STORIES.md`](docs/USER_STORIES.md) |
| Storyboard | [`docs/STORYBOARD.md`](docs/STORYBOARD.md) |
| Wireframes | [`docs/WIREFRAMES.md`](docs/WIREFRAMES.md) |
| Storybook inventory | [`docs/STORYBOOK.md`](docs/STORYBOOK.md) |
| UML / ERD / data model | [`docs/UML.md`](docs/UML.md), [`docs/ERD.md`](docs/ERD.md), [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) |
| API contract | [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) |
| Security and threat model | [`docs/SECURITY.md`](docs/SECURITY.md), [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) |
| Testing and operability | [`docs/TEST_STRATEGY.md`](docs/TEST_STRATEGY.md), [`docs/OPERABILITY.md`](docs/OPERABILITY.md) |
| Traceability | [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md) |
| Architecture decisions | [`docs/adr/README.md`](docs/adr/README.md) |
| Research / standards basis | [`docs/doctoring/REFERENCES.md`](docs/doctoring/REFERENCES.md) |

## Contributing and support

Start with [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md), the PRD, and the applicable ADR/traceability document before changing a product contract. Keep source, tests, documentation, and public claims aligned to the same repository revision.

Security controls and trust boundaries are documented in [`docs/SECURITY.md`](docs/SECURITY.md). To report a suspected vulnerability, follow the [ContextualWisdomLab security policy](https://github.com/ContextualWisdomLab/.github/blob/main/SECURITY.md) and do not disclose it through a public issue. Product and integration defects should be tracked in this repository only when Orgmetra owns the failing boundary; otherwise repair the dedicated owner instead of adding a local workaround.

## License

Orgmetra is licensed under the [Apache License 2.0](LICENSE). See [`NOTICE`](NOTICE) for repository attribution information.
