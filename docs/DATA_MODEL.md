# Data Model

## Core concepts

| Entity | Purpose |
|---|---|
| `tenant_record` | Durable customer/tenant isolation anchor used by referential integrity and row-level security. |
| `person_record` | Durable person entity inside Orgmetra, not an authentication subject. |
| `employment_record` | Durable employment identity for a person. |
| `employment_record_version` | Bitemporal employment status, exclusive-or-concurrent code, and effective period. |
| `organization_unit` | Durable organizational identity referenced by positions and hierarchy facts. |
| `organization_unit_version` | Bitemporal organizational name, type, and parent relationship for an organization unit. |
| `job_profile` | Durable job identity referenced by positions, criteria, and decisions. |
| `job_profile_version` | Bitemporal title, family, and version definition for a job profile. |
| `position_record` | Durable seat identity that keeps stable organization and job references. |
| `position_record_version` | Bitemporal position status and effective period. |
| `assignment_record` | A person's allocation to a position through one employment. |
| `candidate_profile` | Applicant/candidate record before hire. |
| `candidate_worker_link` | Append-only linkage from candidate to worker after hiring. |
| `criterion_blueprint` | Job-related performance criterion definition. |
| `criterion_observation` | Observed criterion result. |
| `decision_evidence_set` | Versioned evidence-set header whose database-computed digest and membership are sealed by one accountable selection decision. |
| `selection_decision_evidence` | Immutable versioned evidence member belonging to one open decision evidence set. |
| `selection_decision` | Human-accountable high-impact decision bound to exactly one sealed evidence set. |
| `validity_study` | Study registry linking its criterion definition to exact decisions, sealed evidence sets, and observed outcomes. |
| `validity_study_decision_link` | Append-only study-to-selection-decision relationship. |
| `validity_study_evidence_set_link` | Append-only study-to-versioned-evidence relationship. |
| `validity_study_outcome_link` | Append-only study-to-criterion-observation relationship. |
| `audit_event_record` | Append-only, tenant-scoped canonical audit envelope bytes plus database-verified SHA-256 digest. |
| `outbox_delivery_record` | Mutable asynchronous delivery coordination for one immutable audit event and delivery target, including immutable database-owned retry budget. |
| `outbox_delivery_escalation_record` | Append-only terminal-failure evidence for one dead-lettered delivery, including failure classification, terminal attempt count, and opaque escalation reference. |

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

Durable anchors such as `organization_unit`, `job_profile`, `employment_record`, and `position_record` do not repeat mutable descriptive attributes. Their descriptive versions live in `organization_unit_version`, `job_profile_version`, `employment_record_version`, and `position_record_version`. Single-valued bitemporal version families reject overlapping effective/system intervals, so one `effective_from`/`effective_to` interval combined with one `recorded_from`/`recorded_to` interval cannot yield contradictory current descriptions. Corrections close the previous recorded interval and insert a replacement; in-place business mutation is rejected.

Assignments remain a legitimately multiple-membership fact. Each assignment must name the covering employment and the same person as that employment. Exclusive employments for one person cannot overlap; a second job must be marked `concurrent`. Allocation totals for one employment, and visible allocations for one position, are enforced by `orgmetra_hris_kernel` rather than a single-valued exclusion. An assignment day must also land on an `active` or `open` position version.

## High-impact decision evidence

Evidence membership is constructed in `selection_decision_evidence` while its `decision_evidence_set` is open. An open set has no caller-supplied content digest. Finalizing `selection_decision` requires at least one versioned evidence member, canonicalizes the members by `(evidence_reference, evidence_version_code)`, computes SHA-256 inside PostgreSQL, and atomically stores that digest while binding `sealed_selection_decision_id`. Database triggers reject later evidence inserts, second-decision reuse, arbitrary post-seal mutation, and a sealed-set pointer that does not resolve back to the decision that consumed that exact set. This makes the stored digest evidence about database-observed membership at finalization rather than an unverified client assertion.

Validation-study link tables preserve the exact decisions, evidence sets and criterion observations included in a study. External specialist results remain references through published contracts; Orgmetra does not reach into a specialist service's application tables.

## Audit and outbox normalization

`audit_event_record`, `outbox_delivery_record`, and `outbox_delivery_escalation_record` are deliberately separate relations. The audit relation stores the immutable, PII-minimized canonical CloudEvents representation and its SHA-256 digest. The database allowlists the event shape, verifies event and tenant identifiers, requires accountable human confirmation when `data.high_impact` is true, and recomputes the digest over the exact stored UTF-8 text before accepting the row.

`outbox_delivery_record` stores only delivery coordination: target, state, attempt count, immutable `maximum_attempt_count`, availability, lease metadata, bounded failure code, and terminal delivery time. Migration 0006 gives existing/new deliveries a default maximum of 5 and constrains the persisted budget to 1 through 100; the transition guard prevents changing it later. It references the immutable audit event through a tenant-qualified foreign key. A unique tenant/event/target key prevents duplicate delivery work for the same target. The guarded lifecycle is `pending -> leased -> delivered`, with `leased -> pending` available for a recorded retry while attempts remain, `leased -> leased` allowed only for expired-lease takeover while attempts remain, and `leased -> dead_lettered` allowed only after the stored retry budget is exhausted and matching escalation evidence exists. Delivered and dead-lettered rows are terminal. Once `delivery_attempt_count` reaches `maximum_attempt_count`, retry and claim cannot create attempt N+1; an expired final lease remains associated with its recorded stable worker reference for terminalization. This separation prevents retry mechanics from becoming mutable audit history and avoids repeating the event payload per delivery target.

`outbox_delivery_escalation_record` is normalized terminal evidence rather than another queue. Exactly one escalation row may bind to one tenant/delivery pair. It captures an operational UUID, lower `snake_case` terminal failure code, namespaced opaque escalation reference, durable terminal attempt count, and recorded time. The row is append-only and forced through the same tenant RLS contract. A deferred binding constraint rejects the row unless its referenced delivery commits as matching terminal `dead_lettered` state with the same attempt count and failure code. It does not duplicate canonical event bytes or mutable HR payloads.

`record_audit_outbox_event(...)` inserts the audit and delivery rows in one statement. It is called by the owning service inside the same PostgreSQL transaction as the authoritative business mutation. If the outbox insert fails, the audit insert from that statement rolls back; if a later business-transaction statement fails, the transaction owner must roll back the entire mutation/audit/outbox unit.

`claim_outbox_delivery(...)` claims due work with deterministic `FOR UPDATE ... SKIP LOCKED`, bounded future leases, and explicit expired-lease recovery evidence only while the stored attempt budget remains. `complete_outbox_delivery(...)` requires the exact owner of a still-live lease. `retry_outbox_delivery(...)` has the same live-owner requirement and also rejects exhausted work. `dead_letter_outbox_delivery(...)` reads, rather than accepts from the dispatcher, the immutable `maximum_attempt_count` before it atomically writes escalation evidence and terminally removes the delivery from normal dispatch. Before exhaustion an expired owner must reclaim normally; after exhaustion only the exact recorded worker reference may close its expired final lease, which avoids both attempt N+1 and foreign-worker takeover. The transition guard independently requires the same exhausted-budget and escalation-binding invariants so structurally valid direct table DML cannot omit them.

Exponential/backoff policy selection, policy-specific producer configuration, audited operator takeover for a permanently lost final-worker identity, retention/export, and external delivery receipts are not yet represented as production-complete behavior on the stacked branch.

## PII policy

PII is not globally masked. Instead, every sensitive read is evaluated against tenant, actor, role, purpose, resource, field sensitivity, legal basis, retention, and audit policy. Audit envelopes and escalation evidence store opaque references and governance codes instead of duplicating mutable employee or candidate payloads.
