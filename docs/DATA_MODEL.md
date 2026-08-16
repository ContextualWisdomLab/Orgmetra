# Data Model

## Core concepts

| Entity | Purpose |
|---|---|
| `tenant_record` | Durable customer/tenant isolation anchor used by referential integrity and row-level security. |
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
| `decision_evidence_set` | Versioned evidence-set header whose digest and membership are sealed by one accountable selection decision. |
| `selection_decision_evidence` | Immutable versioned evidence member belonging to one open decision evidence set. |
| `selection_decision` | Human-accountable high-impact decision bound to exactly one sealed evidence set. |
| `validity_study` | Study registry linking its criterion definition to exact decisions, sealed evidence sets, and observed outcomes. |
| `validity_study_decision_link` | Append-only study-to-selection-decision relationship. |
| `validity_study_evidence_set_link` | Append-only study-to-versioned-evidence relationship. |
| `validity_study_outcome_link` | Append-only study-to-criterion-observation relationship. |

## Tenant integrity

Every owned HRIS fact stores `tenant_record_id`. Parent identities expose tenant-qualified unique keys and child relations use composite `(tenant_record_id, resource_id)` foreign keys. This prevents a row from referencing an otherwise valid resource owned by a different tenant. Forced PostgreSQL row-level security independently filters each tenant-scoped table from `orgmetra.tenant_record_id`; absence of transaction/request tenant context exposes no tenant rows to the application role.

Tenant context is authority supplied by the authenticated application boundary. It is not accepted as sufficient authorization by itself: actor, purpose, operation scope, resource, field sensitivity, legal basis, retention and audit policy remain separate decisions.

## Bitemporal fields

Effective-dated fact tables use:

- `effective_from`
- `effective_to`
- `recorded_from`
- `recorded_to`

Intervals are half-open and non-empty: an end value, when present, must be strictly later than its start. `effective_*` describes real-world validity. `recorded_*` describes when Orgmetra knew the fact.

Durable anchors such as `organization_unit` and `job_profile` do not repeat mutable descriptive attributes. Their descriptive versions live in `organization_unit_version` and `job_profile_version`. Single-valued bitemporal version families reject overlapping effective/system coordinates, so one `effective_at` plus `known_at` coordinate cannot yield contradictory current descriptions. Corrections close the previous recorded interval and insert a replacement; in-place business mutation is rejected.

Assignments remain a legitimately multiple-membership fact and therefore use allocation rules rather than the single-valued exclusion policy.

## High-impact decision evidence

Evidence membership is constructed in `selection_decision_evidence` while its `decision_evidence_set` is open. Finalizing `selection_decision` atomically seals the referenced set and binds its `sealed_selection_decision_id`; database triggers reject later evidence inserts and second-decision reuse. The set stores a version code, digest algorithm and content digest so the human confirmation can point to an exact evidence version rather than a mutable collection.

Validation-study link tables preserve the exact decisions, evidence sets and criterion observations included in a study. External specialist results remain references through published contracts; Orgmetra does not reach into a specialist service's application tables.

## PII policy

PII is not globally masked. Instead, every sensitive read is evaluated against tenant, actor, role, purpose, resource, field sensitivity, legal basis, retention, and audit policy.
