# Job grade persistence traceability

## State boundary

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not persist enterprise-local Job grade assignments.
- **Dependency-active truth:** PR #101 exact head `204311a9678526c6575c9b3625b494c825531a4e` defines the governed `JobGradeDesignReviewPacket` and is not yet integrated.
- **This active stacked PR:** persists normalized Job-grade assignment truth and consumes the exact #101 canonical review contract. It is not protected-main truth.

## Requirement → evidence

| Requirement | Owner evidence |
|---|---|
| Job grade is scoped to authoritative Job, not Person/Position/Assignment | `job_grade_assignment_record.job_profile_id` tenant-qualified FK and one durable anchor per Job |
| Grade/band semantics are enterprise-local and evidence-versioned | immutable `job_grade_definition_record` with exact `grade_code`, `band_code`, definition SHA-256 |
| Job Analysis provenance is authoritative | insert guard re-resolves same-tenant `analysis_validated` snapshot for the same Job and exact content digest |
| Human review cannot be replaced by a free-standing digest | exact bounded canonical `JobGradeDesignReviewPacket` JSON is stored, SHA-256 verified, parsed, key-set checked, and matched to typed persisted scope |
| Requester/reviewer separation is preserved | UUIDv4 actor constraints, typed columns, canonical packet equality and inequality check |
| Purpose/reason/evidence versioning are explicit | fixed `job_grade_design_review`, controlled reason code, positive bounded evidence version, exact canonical packet binding |
| Audit/outbox evidence is immutable and semantically exact | same-tenant `audit_event_record`, exact purpose/reason/reviewer/evidence/subject/time/result, `integration_hub` outbox requirement |
| Business time and system-recorded time are separate | `effective_from/effective_to` independent from PostgreSQL-owned `recorded_from/recorded_to` |
| Historical correction is not rewrite | bitemporal exclusion, close-only current-transaction update guard, DELETE/TRUNCATE rejection |
| Tenant isolation fails closed | ENABLE + FORCE RLS on definition, assignment anchor, and assignment version; `NOSUPERUSER NOBYPASSRLS` regression; migration and trigger functions pin trusted `search_path` |
| Job grade does not grant high-impact downstream authority | fixed `decision_authority_state=not_authorized_for_compensation_or_employment_decision` |

## Executable evidence

`tests/test_job_grade_persistence_postgres.sh` is the dedicated PostgreSQL acceptance contract. It covers the happy path plus wrong-grade review binding, cross-Job Job Analysis reuse, caller-backdated system time, in-place history rewrite, immutable definition rewrite, TRUNCATE resistance, trusted trigger `search_path` pinning, and tenant visibility under a `NOSUPERUSER NOBYPASSRLS` reader.

`.github/workflows/job-grade-persistence-quality.yml` checks out the exact PR head, prints deterministic source provenance, runs the PostgreSQL acceptance contract, and requires a clean checkout. Focused stack-local GREEN does not substitute for Foundation/SAST/Security/Recovery and full post-parent-integration evidence.

## Next integration action

Process #101 dependency-first. After #101 integrates, retarget this PR to the then-current protected `develop`, resolve only real conflicts, refetch exact head/base/rules/reviews/threads, and rerun all applicable current-head evidence without transferring #101 checks or reviews.
