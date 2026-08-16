# ERD

```mermaid
erDiagram
    person_record ||--o{ person_name_record : named_by
    person_record ||--o{ employment_record : has
    employment_record ||--o{ employment_version : versioned_as
    organization_unit ||--o{ organization_unit_version : versioned_as
    job_profile ||--o{ job_profile_version : versioned_as
    organization_unit ||--o{ position_record : contains
    job_profile ||--o{ position_record : defines
    position_record ||--o{ position_version : versioned_as
    person_record ||--o{ assignment_record : receives
    employment_record ||--o{ assignment_record : staffs_through
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

Durable anchors (`person_record`, `employment_record`, `organization_unit`, `job_profile`, `position_record`) do not store mutable descriptive facts. Version tables carry effective time and system-recorded time. `assignment_record` names both the person and the employment so rehire and dual employment stay distinguishable.

## Naming contract

All persisted object names use descriptive two-or-more-word `snake_case` identifiers. Single-token database object names are prohibited unless required by an external standard and approved by ADR.
