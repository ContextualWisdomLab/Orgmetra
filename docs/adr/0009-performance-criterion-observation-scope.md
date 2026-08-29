# ADR 0009: Performance criterion observations require worker-job scope

Status: Accepted

## Context

Protected Orgmetra already stores `performance_cycle`, `criterion_blueprint`, and `criterion_observation` as tenant-scoped temporal records. The baseline foreign keys prove that an observation's person, cycle, and criterion all belong to the same tenant, but they do not prove that the criterion belongs to a Job the worker actually held when the performance was observed. They also do not prove that the observation falls inside the effective performance cycle or that a stale assignment anchor is still backed by eligible employment and a staffable Position.

That gap is material. Criterion observations feed performance management and criterion-related validation. The U.S. Equal Employment Opportunity Commission's Uniform Guidelines define criterion-related validity around a demonstrated relationship with important elements of job performance, while the U.S. Office of Personnel Management states that job-analysis information supports performance appraisals and other personnel actions. A cross-Job or out-of-period outcome can therefore contaminate both operational performance records and downstream validity evidence even when every foreign key is technically valid.

The governing references are already recorded in `docs/doctoring/REFERENCES.md` in APA 7 form: Equal Employment Opportunity Commission (1978), *Uniform guidelines on employee selection procedures*, 29 C.F.R. Part 1607; and U.S. Office of Personnel Management (n.d.), *Job analysis*.

## Decision

1. `criterion_observation` remains an evidence record, not an automated employment decision.
2. Every new observation must reference a criterion blueprint that is effective on the observation's business-date coordinate and current in system-recorded time.
3. Every new observation must fall inside the referenced performance cycle's effective interval, using the same current-recorded-time rule.
4. The observed person must have at least one current-recorded `assignment_record` effective on that date whose `position_record.job_profile_id` equals the criterion blueprint's `job_profile_id`.
5. The same matching assignment must also be backed at that coordinate by a current-recorded `employment_record_version` whose status is `active` or `leave` and a current-recorded `position_record_version` whose status is `active` or `open`. These are the assignment-eligibility and staffable-seat semantics already owned by the HRIS kernel; a stale assignment anchor alone is insufficient performance context.
6. The database owns these invariants through `enforce_criterion_observation_scope()` and `criterion_observation_scope_guard`; application callers cannot opt out by choosing a different code path.
7. The trigger uses a fixed `pg_catalog, public` search path so caller-controlled schema precedence cannot shadow the referenced relations or built-ins.
8. Until the foundation introduces an explicit tenant-local business-date field, the date coordinate derived from `observed_at` is the UTC calendar date. This is deterministic across sessions and prevents `TimeZone` changes from moving the same evidence instant across an effective-period boundary. A future localization migration must introduce an explicit business-date contract rather than silently reinterpret historical observations.
9. Existing bitemporal mutation guards remain authoritative. This ADR adds insert-time scope integrity; it does not weaken correction history or row-level tenant isolation.
10. No additional PII is copied into the scope check. It operates only on opaque record identifiers, status codes, and temporal/job relationships.
11. Any downstream high-impact employment decision that consumes a performance outcome still requires the separately governed human confirmation, actor, purpose, reason, evidence-version, and immutable audit controls. Passing this scope guard is necessary evidence hygiene, never sufficient authority for a decision.
12. An observation's system-recorded instant must not precede its `observed_at` instant. The trigger rejects that impossible chronology before it uses the observation's business-time coordinate for any scope lookup.
13. Migration `0014_criterion_observation_chronology.sql` applies this chronology guard to databases that already installed migration `0011`; it replaces the function body without dropping or recreating `criterion_observation_scope_guard`.

## Rejected alternatives

### Trust the service layer

Rejected because direct database writers, migration tooling, or future adapters could bypass service-only validation and persist scientifically invalid outcomes.

### Validate only tenant equality

Rejected because same-tenant records can still describe different Jobs or periods. Tenant integrity is necessary but does not establish criterion relevance.

### Trust an assignment anchor without employment and position versions

Rejected because an assignment can outlive the business state that made it valid. A terminated employment or frozen/closed/abolished Position must not silently remain eligible performance context merely because an assignment row was not yet closed.

### Add a second denormalized Job identifier to `criterion_observation`

Rejected because `criterion_blueprint` already owns the criterion-to-Job relationship. Duplicating that identifier would create update anomalies rather than improve 3NF.

### Infer the Job later during a validity study

Rejected because invalid raw observations would already be admitted to the authoritative HCM record and could affect performance reporting before a validity-study workflow sees them.

## Evidence

`tests/test_criterion_observation_scope_postgres.sh` is the executable acceptance contract. It first established the RED condition against the protected baseline: a worker assigned to Job A could receive a criterion observation for Job B. A second RED hardening cycle proved that checking only the assignment anchor still admitted outcomes while the Position was frozen or after the employment was terminated. The repaired contract must reject those cases, reject an observation dated before the worker's relevant assignment, reject an observation whose system-recorded instant precedes `observed_at`, reject an observation outside the performance cycle, and persist an in-cycle observation for the worker's actually assigned Job while both employment and Position remain eligible. It also closes each current-recorded lookup (`criterion_blueprint`, `performance_cycle`, `assignment_record`, `position_record`, `employment_record_version`, and `position_record_version`) inside an aborting transaction and requires rejection, then proves UTC calendar-date conversion under non-UTC session `TimeZone` at the UTC midnight assignment-start accept path and the last UTC instant of the prior day. The dedicated exact-head workflow step exercises the impossible recorded-before-observed chronology.

The hosted PostgreSQL contract is required to run from the exact PR head. Queued, stale, predecessor, status-only, or model-only evidence is non-passing.

## Consequences

Performance and validation consumers can rely on each newly admitted criterion observation having a database-enforced Job, temporal, employment-eligibility, and staffable-Position relationship to the worker. Multiple-membership employment remains supported because any single effective matching assignment with both required coverage facts may satisfy the Job relationship. The slice intentionally does not define rating scales, aggregate performance decisions, psychometric models, or UI; those remain separate bounded capabilities.
