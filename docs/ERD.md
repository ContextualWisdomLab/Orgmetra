# ERD

```mermaid
erDiagram
    person_record ||--o{ person_name_record : has_names
    person_record ||--o{ employment_record : has
    organization_unit ||--o{ position_record : contains
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
    selection_decision ||--|{ selection_decision_evidence : cites
    criterion_blueprint ||--o{ validity_study : validated_by
    person_record ||--o{ compensation_record : has
    employment_record ||--o{ employment_transition : changes_through
```

## Cardinality decisions

A candidate profile can be linked to at most one worker identity because `candidate_profile_id` is unique in `candidate_worker_link`. A person identity can have multiple candidate-worker links across reapplications or historical candidate profiles, so the person-side cardinality is one-to-many.

Each criterion observation belongs to one effective-dated performance cycle so reporting periods remain reconstructable across effective and system time.

A selection decision requires one or more immutable evidence-reference rows. Evidence versions are stored separately from the decision header to preserve 3NF and permit an auditable evidence set without repeating decision attributes.

## Naming contract

All persisted object names use descriptive two-or-more-word `snake_case` identifiers. Single-token database object names are prohibited unless required by an external standard and approved by ADR.
