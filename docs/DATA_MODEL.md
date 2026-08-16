# Data Model

## Core concepts

| Entity | Purpose |
|---|---|
| `person_record` | Durable person entity inside Orgmetra, not an authentication subject. |
| `person_name_record` | One effective and system-recorded version of a person's name. |
| `employment_record` | Durable employment relationship for a person. |
| `employment_version` | One bitemporal status version of that employment. |
| `organization_unit` | Durable organizational identity. |
| `organization_unit_version` | One bitemporal name, type, and parent version. |
| `job_profile` | Durable enterprise job identity. |
| `job_profile_version` | One bitemporal definition of work. |
| `position_record` | Durable seat in an organization that instantiates a job profile. |
| `position_version` | One bitemporal status version of that seat. |
| `assignment_record` | A person's allocation to a position through one employment. |
| `candidate_profile` | Applicant/candidate record before hire. |
| `candidate_worker_link` | Append-only linkage from candidate to worker after hiring. |
| `criterion_blueprint` | Job-related performance criterion definition. |
| `criterion_observation` | Observed criterion result. |
| `selection_decision` | Human accountable decision with evidence references. |
| `validity_study` | Study linking selection evidence to outcomes. |

## Bitemporal fields

Every effective-dated version table uses:

- `effective_from`
- `effective_to`
- `recorded_from`
- `recorded_to`

`effective_*` describes real-world validity. `recorded_*` describes when Orgmetra knew the fact. Historical queries must pass a knowledge-time coordinate and an identity key so two people are never treated as one ambiguous fact.

## Assignment integrity

`assignment_record.allocation_ratio` is `numeric(5,4)`. Portfolio validation counts only rows visible at `known_at`. A person and a position each have capacity one, so job-share is allowed and double full-time occupancy is not. The assignment must name a covering `employment_record` for the same person.

## PII policy

PII is not globally masked. Instead, every sensitive read is evaluated against tenant, actor, role, purpose, resource, field sensitivity, legal basis, retention, and audit policy. Domain errors that cross adapters omit identifiers, dates, and ratios.
