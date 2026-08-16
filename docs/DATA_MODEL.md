# Data Model

## Core concepts

| Entity | Purpose |
|---|---|
| `person_record` | Durable person entity inside Orgmetra, not an authentication subject. |
| `employment_record` | Employment relationship for a person. |
| `organization_unit` | Durable organizational identity referenced by positions and hierarchy facts. |
| `organization_unit_version` | Bitemporal organizational name, type, and parent relationship for an organization unit. |
| `job_profile` | Durable job identity referenced by positions, criteria, and decisions. |
| `job_profile_version` | Bitemporal title, family, and version definition for a job profile. |
| `position_record` | A seat in an organization that instantiates a job profile. |
| `assignment_record` | A person's allocation to a position over time. |
| `candidate_profile` | Applicant/candidate record before hire. |
| `candidate_worker_link` | Append-only linkage from candidate to worker after hiring. |
| `criterion_blueprint` | Job-related performance criterion definition. |
| `criterion_observation` | Observed criterion result. |
| `selection_decision` | Human accountable decision with evidence references. |
| `validity_study` | Study linking selection evidence to outcomes. |

## Bitemporal fields

Every effective-dated fact table uses:

- `effective_from`
- `effective_to`
- `recorded_from`
- `recorded_to`

Intervals are half-open and non-empty: an end value, when present, must be strictly later than its start. `effective_*` describes real-world validity. `recorded_*` describes when Orgmetra knew the fact.

Durable anchors such as `organization_unit` and `job_profile` do not repeat mutable descriptive attributes. Their descriptive versions live in `organization_unit_version` and `job_profile_version`, preserving 3NF while allowing retroactive corrections without overwriting prior knowledge.

## PII policy

PII is not globally masked. Instead, every sensitive read is evaluated against tenant, actor, role, purpose, resource, field sensitivity, legal basis, retention, and audit policy.
