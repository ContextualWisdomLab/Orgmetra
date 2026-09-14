# PostgreSQL Employment-history read traceability

**Lifecycle status:** Active stacked PR #156 only. This document does not claim protected-`develop` integration or hosted exact-head GREEN.

## Buyer problem

PR #155 defines a customer-callable, purpose-bound Employment-history read but leaves persistence injected. Without a canonical adapter, an Orgmetra deployment cannot obtain that bounded history from normalized `employment_record` and `employment_record_version` truth without bespoke host code.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| No DB access on invalid input | exact tenant/Person UUID and built-in UTC `known_at` validation before `connection_factory()` | invalid UUID/time cases assert zero connection calls |
| Database cannot mutate HR truth | `_READ_ONLY_SQL`: `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY` | fake DB-API execution-order assertion plus source-exact PostgreSQL write rejection |
| Tenant defense in depth | `_TENANT_CONTEXT_SQL` sets transaction-local `orgmetra.tenant_record_id` before SELECT | fake DB-API parameter assertion plus source-exact PostgreSQL execution |
| Explicit Employment/Person scope | fully qualified join between `public.employment_record_version` and `public.employment_record` with tenant/Person predicates | unit SQL assertions plus seeded foreign-tenant Person returns no row |
| Preserve system knowledge | half-open parent/version `recorded_from`/`recorded_to` predicates at `known_at` | unit visibility rejection plus real PostgreSQL pre/post-correction and exact boundary reconstruction |
| Preserve business history | no effective-date filter; deterministic effective start/Employment/version ordering | returned typed dates, SQL ordering assertion, and two system-time versions of one Employment fixture |
| Canonical UTC | `AT TIME ZONE 'UTC'` projection and exact naive DB timestamp validation | malformed timestamp unit regressions plus real PostgreSQL queries under `Asia/Seoul` and `Pacific/Honolulu` session time zones |
| Untrusted DB-API boundary | exact list result, exact tuple row shape, domain reconstruction | malformed collection/row/value unit regressions |
| Immutable typed result | tuple of `EmploymentHistoryRecord` values | empty and non-empty result regressions |
| Parent authority remains single owner | adapter accepts no purpose or authorization input | PR #155 performs authorization and service revalidation |

## Test-first and repair chain

1. **Contract-only child head:** `1a8b9fb7` added adapter regressions while `orgmetra_people_api.postgres_employment_history` was absent.
2. **Expected RED:** the owning module was missing; predecessor or parent failures are not relabeled as adapter evidence.
3. **Implementation:** the child adds the adapter and package-root export; the People unit suite owns exact input, DB-API, row-integrity, visibility, and domain-reconstruction behavior.
4. **Evidence audit:** the retired `employment-history-postgres-quality.yml` was inspected and found not to start PostgreSQL or execute the adapter against a database. Its prior “real PostgreSQL” implication was removed from acceptance authority.
5. **Canonical database contract:** #156 ordinary-forwarded onto #155 `8d7871bd41b98c1f09bade8c17260d8e1b297daf` and extended the already Foundation-owned `tests/test_bitemporal_postgres.sh`. The shell contract parses production `postgres_employment_history.py`, extracts `_READ_ONLY_SQL`, `_TENANT_CONTEXT_SQL`, and `_EMPLOYMENT_HISTORY_SQL`, rejects placeholder/statement drift, binds psql variables, and executes those exact statements against seeded PostgreSQL 16.14 when canonical Foundation runs.
6. **Real-database assertions:** the contract seeds one concurrent Employment with adjacent system-recorded versions and a foreign-tenant Person/Employment fixture; verifies pre-correction, post-correction, exact `[recorded_from, recorded_to)` boundary, non-UTC session-time behavior, foreign-target exclusion, and read-only write rejection.
7. **Hosted evidence rule:** #156 remains stacked on #155, while the canonical Foundation pull-request trigger targets `develop`. Therefore the source-level real-database contract exists but has not yet produced hosted exact-head PostgreSQL evidence for this stack. After the owner stack reaches protected `develop`, #156 must retarget and reacquire Foundation plus applicable security/review gates; parent/predecessor results do not transfer.

## Evidence interpretation

`services/people-api/tests/test_postgres_employment_history.py` remains a fake DB-API unit contract and must not be described as a real PostgreSQL run. Conversely, the PostgreSQL shell contract intentionally does not claim to exercise psycopg connection/pool behavior; it executes the exact production SQL constants against PostgreSQL and leaves Python connection/cursor semantics to the unit suite. Existing `test_tenant_isolation_postgres.sh` remains the authority for forced-RLS behavior under non-bypass application roles; the Employment-history query's explicit tenant predicates are defense in depth, not a substitute for that RLS proof.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It does not join organization, Job, Position, Assignment, compensation, candidate, performance, credential, prompt, or model-output data. Purpose-bound authorization-before-retrieval remains in the parent service; the adapter performs no mutation, audit/outbox write, or high-impact employment decision.

## Out of scope

- Employment-history HTTP/presentation integration; PR #155 owns that boundary.
- Employment mutation or correction workflows.
- New database migrations; the protected schema already owns these relations and RLS policies.
- Release, tag, publication, or protected-branch authority.
