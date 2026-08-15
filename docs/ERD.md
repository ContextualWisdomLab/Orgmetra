# ERD

```mermaid
erDiagram
    person_record ||--o{ employment_record : has
    organization_unit ||--o{ position_record : contains
    job_profile ||--o{ position_record : defines
    person_record ||--o{ assignment_record : receives
    position_record ||--o{ assignment_record : assigned_through
    candidate_profile ||--o| candidate_worker_link : may_become
    person_record ||--o| candidate_worker_link : links_worker
    job_profile ||--o{ criterion_blueprint : requires
    criterion_blueprint ||--o{ criterion_observation : produces
    person_record ||--o{ criterion_observation : observed_for
    candidate_profile ||--o{ selection_decision : receives
    job_profile ||--o{ selection_decision : targets
    criterion_blueprint ||--o{ validity_study : validated_by
    person_record ||--o{ compensation_record : has
    employment_record ||--o{ employment_transition : changes_through
```

## Naming contract

All persisted object names use descriptive two-or-more-word `snake_case` identifiers. Single-token database object names are prohibited unless required by an external standard and approved by ADR.
