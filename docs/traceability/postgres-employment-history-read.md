# PostgreSQL Employment-history read traceability

**Lifecycle status:** Active stacked PR #156 only. This document does not claim protected-`develop` integration or hosted exact-head GREEN.

## Buyer problem

PR #155 defines a customer-callable, purpose-bound Employment-history read but leaves persistence injected. Without a canonical adapter, an Orgmetra deployment cannot obtain that bounded history from normalized `employment_record` and `employment_record_version` truth without bespoke host code.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| Stable executable DB capability | exact accepted `connection_factory` stored in immutable tuple payload and invoked by direct tuple access | post-construction `object.__setattr__` replacement must raise and the originally accepted factory is the only capability called |
| Safe retained UUID authority | exact UUID wrapper → single `.int` read → exact built-in integer/range proof → fresh UUID reconstruction before external capability | forged executable `.int` payload fails before comparison/DB access; connection-time mutation of caller-owned UUID aliases cannot retarget tenant/Person SQL parameters |
| No DB access on invalid input | exact tenant/Person UUID scalar validation and built-in UTC `known_at` validation before `connection_factory()` | invalid UUID/time cases assert zero connection calls |
| Actual transaction before transaction-local controls | returned connection must expose exact `autocommit is False` before cursor acquisition | autocommit, missing, integer-zero, and string-false modes fail before cursor/SQL access |
| Database cannot mutate HR truth | `_READ_ONLY_SQL`: `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY` inside the proven non-autocommit connection transaction | fake DB-API execution-order assertion plus source-exact PostgreSQL write rejection |
| Tenant defense in depth | `_TENANT_CONTEXT_SQL` sets transaction-local `orgmetra.tenant_record_id` before SELECT in the same transaction | fake DB-API parameter assertion plus source-exact PostgreSQL execution |
| Explicit Employment/Person scope | fully qualified join between `public.employment_record_version` and `public.employment_record` with tenant/Person predicates | unit SQL assertions plus seeded foreign-tenant Person returns no row |
| Preserve system knowledge | half-open parent/version `recorded_from`/`recorded_to` predicates at `known_at` | unit visibility rejection plus real PostgreSQL pre/post-correction and exact boundary reconstruction |
| Preserve business history | no effective-date filter; deterministic effective start/Employment/version ordering | returned typed dates, SQL ordering assertion, and two system-time versions of one Employment fixture |
| Canonical UTC | `AT TIME ZONE 'UTC'` projection and exact naive DB timestamp validation | malformed timestamp unit regressions plus real PostgreSQL queries under `Asia/Seoul` and `Pacific/Honolulu` session time zones |
| Untrusted DB-API boundary | exact list result, exact tuple row shape, domain reconstruction | malformed collection/row/value unit regressions |
| Immutable typed result | tuple of `EmploymentHistoryRecord` values | empty and non-empty result regressions |
| Parent authority remains single owner | adapter accepts no purpose or authorization input | PR #155 performs authentication/transport isolation and #149 performs authorization/service revalidation |

## Test-first and repair chain

1. **Contract-only child head:** `1a8b9fb7` added adapter regressions while `orgmetra_people_api.postgres_employment_history` was absent.
2. **Expected RED:** the owning module was missing; predecessor or parent failures are not relabeled as adapter evidence.
3. **Implementation:** the child adds the adapter and package-root export; the People unit suite owns exact input, DB-API, row-integrity, visibility, and domain-reconstruction behavior.
4. **Evidence audit:** the retired `employment-history-postgres-quality.yml` was inspected and found not to start PostgreSQL or execute the adapter against a database. Its prior “real PostgreSQL” implication was removed from acceptance authority.
5. **Canonical database contract:** #156 ordinary-forwarded onto the then-current #155 and extended the already Foundation-owned `tests/test_bitemporal_postgres.sh`. The shell contract parses production `postgres_employment_history.py`, extracts `_READ_ONLY_SQL`, `_TENANT_CONTEXT_SQL`, and `_EMPLOYMENT_HISTORY_SQL`, rejects placeholder/statement drift, binds psql variables, and executes those exact statements against seeded PostgreSQL 16.14 when canonical Foundation runs.
6. **Real-database assertions:** the contract seeds one concurrent Employment with adjacent system-recorded versions and a foreign-tenant Person/Employment fixture; verifies pre-correction, post-correction, exact `[recorded_from, recorded_to)` boundary, non-UTC session-time behavior, foreign-target exclusion, and read-only write rejection.
7. **Capability-integrity RED:** `5a8c95f5942824d712a80ee4261ec320596605ad` adds a focused regression requiring the validated connection factory to resist post-construction replacement and remain the exact executable used by the read.
8. **Capability-integrity repair:** `a41ef5278ef45b15c1ab721244c40b35f828907a` replaces slot-backed dependency storage with immutable tuple payload, exposes only the retained capability view, and invokes the exact tuple-stored callable directly.
9. **Retained-UUID RED:** `16dddcea47c60ceb0e2abc5154ffad5f03c484a2` adds regressions for forged exact UUID retained payloads and connection-time mutation of caller-owned tenant/Person UUID aliases.
10. **Retained-UUID repair:** `0d0993b3a9541cef4ddc7050df47ee55fc318a59` reads `.int` once, proves exact built-in integer authority and the operational range, reconstructs detached UUID values before connection acquisition, and uses only those detached values for SQL and post-read target verification.
11. **Transaction-integrity RED:** `b207e6db14452e36f2428c0fc472f8f5bb98e7a7` requires autocommit or otherwise unproven connection modes to fail before cursor access. `ab34fdcf0b02420219a1133571f87915e6934b8e` and `b1b51fbf241e768536dcbcb2c22a0e0cd443fee5` make accepted test doubles explicitly non-autocommit.
12. **Transaction-integrity repair:** `15c28cfaafd261bdea047961fb5461c641bb8be5` checks exact `autocommit is False` immediately after connection acquisition and before obtaining a cursor. Issue #318 hands the same verified defect to canonical governed-People owner #55 rather than copying child implementation upstream.
13. **Canonical owner restack:** `a2a9f04be385ee2bfb66dc8f5e58306f540ebe8f` ordinary-forward adopted #155 after #149 had inherited canonical #55 retained-identity repair #319.
14. **HTTP parser-hardening adoption:** ordinary two-parent merge `23e2ffb028628d74df7de12196fb8a336b3a68cb` adopted #155 `03030dbccba3b6044e2b4d8201203f309d4f40de` after its oversized-path-before-tokenization repair, without altering #156's PostgreSQL-only delta.
15. **HTTP backend/event-loop adoption:** after #155 test-first `d998cd684adee518b04ddc37cfad7c17ea151d8c` and causal repair `3432b08b67f28cf5e665346494104ec15d523590` fixed the invalid backend-error envelope and moved the synchronous Employment-history service off the ASGI event-loop thread, ordinary two-parent merge `04d1c354d2b7bce972af38d26e64c590a70f0550` adopted current #155 `ef27e2e91e0e73c98f396f13ca8da913484c2927`. The resolved tree takes the four parent-owned HTTP source/test/ADR/traceability files from #155 and preserves all #156-owned PostgreSQL files.
16. **Hosted evidence rule:** #156 remains stacked on #155, while the canonical Foundation pull-request trigger targets `develop`. Therefore the source-level real-database contract and integrity repairs have not yet produced hosted exact-head acceptance evidence for this stack. After the owner stack reaches protected `develop`, #156 must retarget and reacquire Foundation plus applicable security/review gates; parent/predecessor results do not transfer.

## Evidence interpretation

`services/people-api/tests/test_postgres_employment_history.py` and the focused capability/retained-input/transaction regressions remain Python DB-API unit contracts and must not be described as real PostgreSQL runs. Conversely, the PostgreSQL shell contract intentionally does not claim to exercise psycopg connection/pool behavior; it explicitly begins a transaction and executes the exact production SQL constants against PostgreSQL, leaving Python connection/cursor/capability/autocommit semantics to the unit suite. Existing `test_tenant_isolation_postgres.sh` remains the authority for forced-RLS behavior under non-bypass application roles; the Employment-history query's explicit tenant predicates are defense in depth, not a substitute for that RLS proof.

Source-equivalent causal execution reproduces the predecessor forged-payload equality failure and the repaired fail-closed scalar check. A separate retained-alias check shows the reconstructed UUIDs keep the original identities even after caller-owned UUID objects are mutated. The transaction regression demonstrates the intended fail-before-cursor boundary in source. These are causal local contracts, not hosted Foundation evidence.

Current direct parent authority is #155 `ef27e2e91e0e73c98f396f13ca8da913484c2927`; #156 is an ordinary descendant through merge `04d1c354d2b7bce972af38d26e64c590a70f0550` with no intentional parent-owned source duplication. The inherited Employment HTTP parser-order, schema-valid backend-error, and event-loop-isolation repairs remain parent-owned and are not reimplemented in the PostgreSQL adapter.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It does not join organization, Job, Position, Assignment, compensation, candidate, performance, credential, prompt, or model-output data. Purpose-bound authorization-before-retrieval remains in the parent service; the adapter performs no mutation, audit/outbox write, or high-impact employment decision.

The immutable connection-capability binding prevents a dependency that passed construction-time validation from being swapped through ordinary post-construction slot mutation before execution. Scalar detachment prevents forged retained UUID payload behavior and later caller-alias mutation from changing the database target. Exact non-autocommit proof prevents transaction-local controls from being executed on a connection whose statements auto-commit independently. The transaction stays bounded to database setup/query/fetch work rather than spanning authorization or unrelated computation. None of these controls claims sandboxing or protection from arbitrary trusted-process code that fabricates unsupported objects outside the documented constructor boundaries.

## Out of scope

- Employment-history HTTP/presentation integration; PR #155 owns that boundary.
- Employment mutation or correction workflows.
- New database migrations; the protected schema already owns these relations and RLS policies.
- Release, tag, publication, or protected-branch authority.
