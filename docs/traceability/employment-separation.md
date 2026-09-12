# Employment separation traceability

## Scope

This trace binds issue #314 to the first authoritative Employment separation slice. It does not declare rehire (#302) complete. Rehire remains downstream and must create a new Employment for the existing Person after a durable separation exists.

| Requirement | Authority | Executable evidence | Maturity |
|---|---|---|---|
| Correction-not-rewrite separation | ADR 0003 + ADR 0015 | `database/migrations/0014_employment_separation_transition.sql` closes only the expected recorded interval and inserts replacement business-time facts | implemented_on_active_pr |
| One authoritative separation fact | ADR 0015 | `employment_separation_record` links prior, optional continuation and terminal Employment versions; `terminated` successor is the terminal fact while continuation `effective_to` is only its interval boundary | implemented_on_active_pr |
| Exact tenant/Person/Employment/version binding | #314 + ADR 0015 | `separate_employment_record_once(...)` checks tenant context before advisory locking, locks the Employment anchor and requires the expected current-recorded version | implemented_on_active_pr |
| Future Employment facts are not silently cancelled | ADR 0015 | any other current-known Employment version overlapping `[separation_effective_on, infinity)` fails closed and requires owner coordination | implemented_on_active_pr |
| Assignment ownership is preserved | Context Map + ADR 0015 | any Assignment still effective on/after separation fails closed; separation never rewrites Assignment rows | implemented_on_active_pr |
| Database-owned recorded time | #314 | one post-lock `clock_timestamp()` closes prior recorded history, opens replacement versions, stamps separation provenance and is serialized into the audit event `time` | implemented_on_active_pr |
| High-impact governance evidence | ADR 0006 + ADR 0008 + ADR 0015 | controlled reason, evidence reference/version, actor, `workforce_admin` purpose and human confirmation are mandatory; audit/outbox is persisted in the same transaction | implemented_on_active_pr |
| Retry safety | People mutation idempotency contract | exact tenant+route+idempotency-key advisory lock; same semantic command replays first terminal version/timestamp; changed command under same key fails | implemented_on_active_pr |
| Real concurrent-first serialization | #314 | `tests/test_employment_separation_postgres.sh` requires the second backend to expose the first backend through `pg_blocking_pids(...)` while waiting on an advisory lock, then converge on one first result plus one replay | awaiting_foundation_registration |
| Hostile cases | #314 | focused PostgreSQL contract covers cross-tenant context, stale expected version, future-version coordination, open Assignment, same-key semantic conflict and earlier-knowledge reconstruction | awaiting_foundation_registration |
| Canonical CI ownership | #311 | focused PostgreSQL contract must be registered by the Foundation owner after stack reconciliation; this People writer does not duplicate or weaken `.github/workflows/foundation-ci.yml` | awaiting_foundation_registration |
| Rehire | #302 | existing Person + new Employment must cite authoritative prior separation and fresh rehire authority | not_started |

## Current acceptance boundary

`database/migrations/0014_employment_separation_transition.sql`, ADR 0015 and the focused PostgreSQL contract are ordinary-forward changes on the canonical People PR. The existing Foundation workflow remains owned by its canonical Foundation stack, so the new PostgreSQL contract is not treated as hosted GREEN until that owner registers it and an exact-head PostgreSQL run passes.

Static repository validation and unrelated historical checks must not be described as proof of the new separation transaction. Likewise bot review success is review evidence, not runtime acceptance or an independent approval.

## Next owner handoff

Foundation reconciliation should discover `tests/test_employment_separation_postgres.sh` as a PostgreSQL contract rather than adding a filename-specific workflow branch. The execution environment must retain the exact-candidate tree, scrubbed environment, tenant-scoped runtime and immutable provenance rules already owned by #311. Once the owner integrates that contract, the People stack can use the resulting exact-head runtime evidence to decide whether ADR 0015 may move from Proposed to Accepted and whether #314 is ready to hand off to #302.
