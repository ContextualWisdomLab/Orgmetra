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

Active PR #53 includes local People and Job Analysis read views. Editing their
request fields clears displayed values and invalidates pending responses, even
if an edit is reverted. Changing the fixture's personal-details purpose also
clears its prior allowed or denied display; only an explicit review shows a new
outcome. Node and Chromium regressions cover these display boundaries; they do
not establish released authentication or deployment.

Observed default `develop` base `eb9757f8649aaad026a9865508d9aad50c1a7a4f` contains the employment-truth kernel (`packages/hris-kernel/src/orgmetra_hris_kernel/employment.py`), bitemporal workforce-composition snapshot source (`packages/hris-kernel/src/orgmetra_hris_kernel/workforce.py`) and regression source (`packages/hris-kernel/tests/test_workforce_composition.py` and `test_workforce_composition_boundaries.py`), People read/mutation/confirmed-hire source (`services/people-api/src/orgmetra_people_api/people.py`, `mutations.py`, and `hire.py`; `database/migrations/0012_people_mutation_idempotency.sql`), and Job Analysis snapshot read/write source (`services/job-analysis-api/src/orgmetra_job_analysis_api/snapshot.py`; `database/migrations/0013_job_analysis_snapshot.sql`). This is repository source presence only, not configured branch-protection enforcement, newly executed tests, deployed behavior, or a release. Active PR #53 UI remains unmerged; the 2026-08-21 inventory and local execution results in `docs/product-technical-gap-baseline.md` are historical, not current all-PR or release evidence.
