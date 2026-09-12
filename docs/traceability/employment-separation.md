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
| Purpose-bound application authorization | Keyverse adapter + ADR 0015 | `separation.py` authorizes the exact Employment, tenant, `workforce_admin` purpose, `separate_record` operation and `orgmetra.people.write` scope before the persistence port; command and result identities are detached and rebound | implemented_on_active_pr |
| Governed persistence adapter | ADR 0015 | `PostgresEmploymentSeparationPort` starts one READ COMMITTED read/write transaction, binds tenant context, invokes only `separate_employment_record_once(...)`, validates one typed DB result, maps reviewed domain SQLSTATEs, and leaves permission failures operational | implemented_on_active_pr |
| Deny-default SQL capability | ADR 0015 | migrations `0015`/`0016` revoke PUBLIC, create separate `NOLOGIN`/`NOBYPASSRLS` owner and executor roles, move the function to the owner as SECURITY DEFINER, revoke temporary schema CREATE, and grant the executor function EXECUTE only | implemented_on_active_pr |
| No direct DML bypass from runtime capability | ADR 0015 | `tests/test_employment_separation_capability_postgres.sh` requires the executor to have no direct SELECT/INSERT/UPDATE/DELETE/TRUNCATE rights on governed People/audit/outbox relations while still crossing the function boundary | awaiting_foundation_registration |
| Capability-test failure isolation | #314 | the unrelated probe role uses collision-resistant per-execution identity; failure cleanup is best-effort without masking the causal error, while nominal success requires strict verified role cleanup | implemented_on_active_pr |
| Real concurrent-first serialization | #314 | `tests/test_employment_separation_postgres.sh` requires the second backend to expose the first backend through `pg_blocking_pids(...)` while waiting on an advisory lock, then converge on one first result plus one replay | awaiting_foundation_registration |
| Hostile cases | #314 | focused PostgreSQL contract covers cross-tenant context, stale expected version, future-version coordination, open Assignment, same-key semantic conflict and earlier-knowledge reconstruction | awaiting_foundation_registration |
| Canonical CI ownership | #311 | both focused PostgreSQL contracts must be registered by the Foundation owner after stack reconciliation; this People writer does not duplicate or weaken `.github/workflows/foundation-ci.yml` | awaiting_foundation_registration |
| Buyer HTTP/OpenAPI journey | #314 | authenticated request parsing, explicit separation confirmation/evidence body, response/error schema, and p95/E2E evidence must consume the application boundary without exposing owner-role or direct-DML capabilities | not_started |
| Rehire | #302 | existing Person + new Employment must cite authoritative prior separation and fresh rehire authority | not_started |

## Current acceptance boundary

`database/migrations/0014_employment_separation_transition.sql`, `0015_employment_separation_capability_hardening.sql`, `0016_employment_separation_executor_capability.sql`, ADR 0015, the application/persistence ports, and the focused PostgreSQL contracts are ordinary-forward changes on the canonical People PR. The runtime-facing database capability is separated from the privileged function owner, so an application principal does not need direct People/audit/outbox DML merely to invoke the transition.

`services/people-api/src/orgmetra_people_api/separation.py` is the application authorization boundary. It does not trust caller-owned identity aliases or backend result identity. `postgres_separation.py` consumes the already-authorized decision and issues no direct People or audit/outbox DML. Operational deployment still has to bind the People database login to the released executor capability; the adapter does not assume or switch into the owner role.

The existing Foundation workflow remains owned by its canonical Foundation stack. The new PostgreSQL contracts are therefore not treated as hosted GREEN until that owner discovers them from the exact candidate tree and an exact-head PostgreSQL run passes. Static repository validation and bot statuses that report skipped review are not runtime acceptance or qualifying independent approval.

## Next owner handoff

Foundation reconciliation should discover `tests/test_employment_separation_postgres.sh` and `tests/test_employment_separation_capability_postgres.sh` as PostgreSQL contracts rather than adding filename-specific workflow branches. The execution environment must retain the exact-candidate tree, scrubbed environment, tenant-scoped runtime and immutable provenance rules already owned by #311.

The People runtime owner must bind its application/database login to `orgmetra_employment_separation_executor` (or an operationally equivalent grant of that released capability) rather than the owner role or direct table DML. Keyverse remains the user/actor authorization backend; the database executor role is only the persistence capability beneath the already-authorized high-impact command.

The next buyer-visible gap is the HTTP/OpenAPI journey. It must preserve the application command's exact Employment/version/date/reason/evidence/confirmation/idempotency contract, sanitize backend errors, and expose replay/recorded-time semantics without leaking privileged database details. It must be added on the canonical People route owner rather than by a parallel service.

Once those owner boundaries are reconciled and exact-head hosted evidence is green, the People stack can decide whether ADR 0015 may move from Proposed to Accepted and whether #314 is ready to hand off to #302.
