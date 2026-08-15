# Data Model

## Core concepts

| Entity | Purpose |
|---|---|
| `person_record` | Durable person entity inside Orgmetra, not an authentication subject. |
| `employment_record` | Employment relationship for a person. |
| `organization_unit` | Effective-dated organizational unit. |
| `job_profile` | Versioned definition of work. |
| `position_record` | A seat in an organization that instantiates a job profile. |
| `assignment_record` | A person's allocation to a position over time. |
| `candidate_profile` | Applicant/candidate record before hire. |
| `candidate_worker_link` | Append-only linkage from candidate to worker after hiring. |
| `performance_cycle` | Effective-dated performance period that schedules criterion observations. |
| `criterion_blueprint` | Job-related performance criterion definition. |
| `criterion_observation` | Observed criterion result linked to one performance cycle. |
| `selection_decision` | Human accountable decision with evidence references. |
| `validity_study` | Study linking selection evidence to outcomes. |

## Bitemporal fields

Every effective-dated table uses:

- `effective_from`
- `effective_to`
- `recorded_from`
- `recorded_to`

`effective_*` describes real-world validity. `recorded_*` describes when Orgmetra knew the fact.

## PII policy

PII is not globally masked. Instead, every sensitive read is evaluated against tenant, actor, role, purpose, resource, field sensitivity, legal basis, retention, and audit policy.
