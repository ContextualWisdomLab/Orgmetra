# ERD

For readability, the diagram renders representative `tenant_record` scoping edges rather than repeating the same edge for every tenant-owned relation. The authoritative tenant-isolation contract is `docs/DATA_MODEL.md`: **every owned HRIS fact** stores `tenant_record_id`, every cross-table reference is tenant-qualified, and forced row-level security applies independently to every tenant-scoped table. This omission is visual only; it does not weaken the relational or authorization contract for employment, candidate, evidence, decision, validation-link, compensation, or transition entities.

```mermaid
erDiagram
    tenant_record ||--o{ person_record : scopes
    tenant_record ||--o{ organization_unit : scopes
    tenant_record ||--o{ job_profile : scopes
    person_record ||--o{ person_name_record : has_names
    person_record ||--o{ employment_record : has
    organization_unit ||--o{ organization_unit_version : has_versions
    organization_unit_version }o--o| organization_unit : may_parent
    organization_unit ||--o{ position_record : contains
    job_profile ||--o{ job_profile_version : has_versions
    job_profile ||--o{ position_record : defines
    person_record ||--o{ assignment_record : receives
    position_record ||--o{ assignment_record : assigned_through
    candidate_profile ||--o| candidate_worker_link : may_become
    person_record ||--o{ candidate_worker_link : links_worker
    job_profile ||--o{ criterion_blueprint : requires
    performance_cycle ||--o{ criterion_observation : schedules
    criterion_blueprint ||--o{ criterion_observation : produces
    person_record ||--o{ criterion_observation : observed_for
    candidate_profile ||--o{ selection_decision : receives
    job_profile ||--o{ selection_decision : targets
    decision_evidence_set ||--|{ selection_decision_evidence : contains
    decision_evidence_set ||--o| selection_decision : sealed_by
    criterion_blueprint ||--o{ validity_study : defines_criterion
    validity_study ||--o{ validity_study_decision_link : includes_decisions
    selection_decision ||--o{ validity_study_decision_link : observed_predictor_policy
    validity_study ||--o{ validity_study_outcome_link : includes_outcomes
    criterion_observation ||--o{ validity_study_outcome_link : supplies_outcome
    validity_study ||--o{ validity_study_evidence_set_link : preserves_evidence
    decision_evidence_set ||--o{ validity_study_evidence_set_link : supplies_evidence
    person_record ||--o{ compensation_record : has
    employment_record ||--o{ employment_transition : changes_through
```

## Cardinality decisions

`organization_unit` and `job_profile` are durable anchors. Mutable names, classifications, parent relationships, titles, families, and version codes live in bitemporal version rows. Positions therefore retain stable organization/job references while retroactive corrections append or supersede version facts rather than rewriting identity. An organization version may reference another durable organization as its parent; self-parenting is rejected at the database boundary.

Every owned HRIS fact carries `tenant_record_id`. Relationships that cross table boundaries use tenant-qualified foreign keys, and row-level security independently filters every tenant-scoped relation. The tenant column is therefore both a referential-integrity boundary and a runtime isolation boundary, not a caller-supplied business attribute.

A candidate profile can be linked to at most one worker identity within its tenant. A person identity can have multiple candidate-worker links across reapplications or historical candidate profiles, so the person-side cardinality is one-to-many.

Each criterion observation belongs to one effective-dated performance cycle so reporting periods remain reconstructable across effective and system time.

A high-impact selection decision seals exactly one versioned `decision_evidence_set`. Evidence members are inserted while the set is open; the decision records the set reference and atomically changes that set to sealed. After sealing, neither new evidence members nor a second decision may reuse that evidence set. This prevents post-decision evidence drift while retaining normalized, version-addressable evidence.

A `validity_study` connects the criterion blueprint to the exact selection decisions, sealed evidence sets, and criterion observations used as outcomes through append-only link relations. This makes predictor/decision-policy evidence and observed outcomes reconstructable without copying specialist-system payloads into Orgmetra.

## Naming contract

All persisted object names use descriptive two-or-more-word `snake_case` identifiers. Single-token database object names are prohibited unless required by an external standard and approved by ADR.
