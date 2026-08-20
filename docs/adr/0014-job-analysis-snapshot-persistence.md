# ADR 0014: Persist governed job-analysis snapshots

- Status: Accepted on active implementation branch
- Date: 2026-08-20
- Owners: Orgmetra Job Analysis / Workforce Validation

## Context

ADR 0007 defines the canonical in-process `JobAnalysisSnapshot` evidence contract. Protected `develop` now also contains the governed People mutation/idempotency slice through migration 0012, so the next persistence migration is 0013. The previous draft persistence lane used historical migration/ADR numbers and overlapped a second proposed job-analysis store; that competing store has been closed rather than shipping two Task/KSAO authorities.

A snapshot that exists only in memory cannot be reread, audited, or bound to the Job, Position, or criterion identities already present in Orgmetra. Job analysis is a systematic examination of work tasks and the competencies required to perform them, with explicit task-to-competency linkage and evidence provenance. When later selection procedures depend on work behaviors or job knowledge, the analysis must remain reviewable evidence rather than an opaque model assertion.

This slice therefore persists one immutable snapshot without making a hiring, promotion, termination, compensation, or other high-impact employment decision. LLM-origin material remains untrusted draft evidence under ADR 0007 and cannot become validated occupational evidence without accountable human review.

## Decision

Orgmetra will persist the canonical `JobAnalysisSnapshot` in migration `0013_job_analysis_snapshot.sql` as tenant-scoped 3NF relations:

- `job_analysis_snapshot` stores the version header, optional Position and criterion scope, accountable review metadata, content digest, and the 1:1 Functional Job Analysis compatibility profile;
- `job_analysis_task_item` stores observable duties and their versioned evidence source;
- `job_analysis_ksao_item` stores knowledge, skill, ability, and other-characteristic requirements and their evidence source;
- `job_analysis_task_ksao_link` stores explicit task-to-KSAO relationships;
- `job_analysis_write_command` stores the caller `Idempotency-Key`, request digest, actor reference, and purpose code so idempotency and authorization context reach the write boundary.

`job_record_id` from the kernel maps to `job_profile.job_profile_id`. Tenant-qualified foreign keys on optional `position_record_id` and `criterion_blueprint_id` enforce tenant and parent identity. Same-Job binding is a separate service-layer invariant: the PostgreSQL adapter resolves `_POSITION_SCOPE_SQL` and `_CRITERION_SCOPE_SQL` and compares each returned `job_profile_id` with the snapshot Job before inserts. Missing parents, cross-tenant parents, or parents bound to a different Job therefore fail closed through the layer that owns that invariant. Writes require purpose-bound authorization (`job_analysis_write` / `orgmetra.job_architecture.write`) and persist audit/outbox evidence in the same database transaction. The snapshot is occupational evidence rather than person PII, so fields are not indiscriminately masked. The read API returns the same governed snapshot document that was persisted.

The stronger provenance and sealing ideas from the superseded parallel case model—source version identity, digest-addressable evidence, explicit human approval, and richer FJA evidence—must be evolved by extending this canonical snapshot contract rather than introducing a second Task/KSAO persistence authority.

## Consequences

### Positive

- Buyers can persist duties, KSAOs, Task–KSAO links, and FJA evidence and read the same snapshot back.
- Later criterion and selection-validity work can bind to an exact digest-addressable job-analysis version.
- Missing Job, Position, or criterion identities cannot silently create orphan evidence.
- Orgmetra retains one canonical Job Analysis storage and API boundary.

### Costs and limitations

- SME workflow, governed O*NET ingestion, retention/export policy, richer source-version registries, and selection-validity computation remain later bounded slices.
- The 1–5 ratings remain contract-level ordinals; local sampling design, rater aggregation, and uncertainty estimation require explicit methodological evidence before consequential use.

## Verification

Tests must prove that the persisted snapshot document equals the posted payload, `Idempotency-Key` is bound at the write port and stored on `job_analysis_write_command`, missing parents fail closed for the expected foreign-key or same-Job scope reason, snapshot UPDATE and DELETE operations are rejected by the append-only guard, cross-tenant snapshot reads return no rows under a `NOSUPERUSER NOBYPASSRLS` role, and `record_audit_outbox_event(...)` is persisted in the same governed write path. The service boundary requires exact 100% owned production statement and branch coverage where the pinned toolchain exposes those metrics, plus a PostgreSQL integration test that applies protected migrations 0001 through 0012 before migration 0013.

## References

The APA 7 bibliography is maintained in `docs/doctoring/REFERENCES.md`, including SIOP Principles, the Uniform Guidelines on Employee Selection Procedures, current O*NET technical documentation, and current OPM job-analysis guidance. Material standards claims must remain tied to the authoritative version recorded there.
