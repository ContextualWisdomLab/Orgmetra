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
- `docs/product-technical-gap-baseline.md`
- `docs/adr/README.md`
- `docs/doctoring/REFERENCES.md`

## Status

Protected `develop` at `9e3e4847510e1e612b48474ba42b177b8ed824df` includes the employment-truth kernel, governed candidate-to-worker conversion, purpose-bound PII authorization, normalized worker-bound validity studies, criterion-observation scope, the governed Naruon intent adapter, requisition review packets, the governed People mutation/confirmed-hire implementation with tenant-scoped idempotency and atomic audit/outbox evidence, and canonical persisted Job Analysis through migration `0013` and the protected Job Analysis API. Workforce-composition evidence remains active PR #54 rather than protected truth. The next protected product gaps are a connected and released browser workspace, statistical validity estimation, and a versioned release; see `docs/product-technical-gap-baseline.md` for exact evidence boundaries and current PR state.
