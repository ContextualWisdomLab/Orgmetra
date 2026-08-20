# Orgmetra

**Evidence-centered HRIS for the full employment lifecycle.**

Orgmetra is the ContextualWisdomLab system of record for people, employment, organizations, jobs, positions, assignments, candidate-to-worker linkage, performance criteria, compensation, and evidence-backed talent decisions.

The product is intentionally federated: specialist CWL products remain independently deployable and integrate through versioned package, API, event, and adapter contracts. Orgmetra does not read another product's application tables directly.

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

- People and employment
- Organization, job, position, and assignment
- Talent acquisition and candidate-worker linkage
- Performance and criterion observations
- Workforce validation and decision evidence
- Audit, provenance, and purpose-bound authorization
- CWL integration hub

## CWL ecosystem boundaries

- Keyverse: identity, OIDC, SCIM, federation
- Naruon: customer-owned mail/calendar/file control plane
- Psychometrics Commons + fast-mlsirm: assessment lifecycle and psychometric computation
- TEPP: temporal, event, multilevel and multiple-membership analysis
- Semantic Data Portal: occupation/skill/ability ontology and semantic catalog
- Contextual Orchestrator: bounded, evidence-grounded AI assistance
- Clearfolio + NewsDOM: document viewing and PDF-to-DOM
- MHTML ETL Gateway + mightyETL: governed migration and CDC
- RankWeave + ThreadWeave + LineageWeave: retrieval, conversation structure and inferred evidence lineage
- Inkspan + DiagramWeave: authoring and diagrams

## Non-negotiable contracts

1. `person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`, and `assignment_record` are separate concepts.
2. Effective time and system-recorded time are preserved independently.
3. Database objects are normalized to 3NF and use descriptive two-or-more-word `snake_case` names.
4. Public identifiers are opaque; credentials are never HR person identifiers.
5. PII required for authorized HR work remains usable. Protection is achieved with purpose-bound authorization, least privilege, encryption, retention and audit rather than indiscriminate masking.
6. LLM output is draft evidence, never an autonomous high-impact employment decision.
7. Inferred lineage is not authoritative audit history.
8. No cross-service application-table access.

## Documentation map

- `docs/PRD.md`
- `docs/TRD.md`
- `ARCHITECTURE.md`
- `docs/USER_STORIES.md`
- `docs/STORYBOARD.md`
- `docs/WIREFRAMES.md`
- `docs/STORYBOOK.md`
- `docs/UML.md`
- `docs/ERD.md`
- `docs/DATA_MODEL.md`
- `docs/API_CONTRACT.md`
- `docs/SECURITY.md`
- `docs/THREAT_MODEL.md`
- `docs/TEST_STRATEGY.md`
- `docs/OPERABILITY.md`
- `docs/TRACEABILITY.md`
- `docs/adr/README.md`
- `docs/doctoring/REFERENCES.md`

## Status

Protected `develop` is the sole shipped repository truth. It includes the normalized bitemporal HRIS foundation; exclusive/concurrent employment and staffable-seat invariants; acyclic organization reconstruction; governed candidate-to-worker conversion; purpose-bound PII authorization; governed People reads plus purpose-bound People mutation and confirmed-hire materialization with atomic audit/outbox evidence and tenant-scoped idempotency; Job/cycle/staffing-scoped criterion observations; normalized validity-study cases; immutable audit and transactional outbox persistence with bounded recovery; bitemporal workforce-composition snapshots; executable PostgreSQL restore rehearsal evidence; governed Naruon calendar intents; governed migration handoff; requisition review; and human selection-review evidence.

Job Analysis persistence remains active-PR truth: the open persistence/API lane carries the Task/FJA/KSAO snapshot implementation and must not be treated as shipped until it integrates into protected `develop`.

`implemented_on_protected_main` is the stable maturity enum for capability evidence integrated into Orgmetra's protected branch; in this repository that protected branch is `develop`. The enum is a compatibility vocabulary value, not a literal Git branch named `main`.

Capabilities on open PRs are not shipped until integrated into protected `develop`. Use `docs/TRACEABILITY.md` as the canonical maturity map and treat `implemented_on_active_pr` as non-protected evidence only.
