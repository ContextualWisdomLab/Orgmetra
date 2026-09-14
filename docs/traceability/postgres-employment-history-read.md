# PostgreSQL Employment-history read traceability

**Lifecycle status:** Active stacked PR #156 only. This document does not claim protected-`develop` integration or hosted exact-head GREEN.

## Buyer problem

PR #155 defines a customer-callable, purpose-bound Employment-history read but leaves persistence injected. #156 supplies the canonical PostgreSQL adapter over normalized `employment_record` and `employment_record_version` truth.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| Stable executable DB capability | accepted `connection_factory` is retained in immutable tuple payload and invoked directly | post-construction capability replacement fails; only accepted factory executes |
| Safe retained identity | tenant/Person UUIDs reduce to exact built-in integer authority before external capability use and are reconstructed detached | forged `.int` payload and caller-alias mutation cannot retarget SQL |
| Proven transaction | exact `connection.autocommit is False` required before cursor acquisition | autocommit/missing/non-bool modes fail before cursor/SQL |
| Read-only tenant-bound DB work | read-only transaction and transaction-local tenant context precede exact Employment-history SELECT | DB-API ordering plus seeded PostgreSQL contract |
| Bitemporal/tenant correctness | explicit tenant/Person predicates, half-open recorded-time visibility, UTC projection, deterministic ordering | real PostgreSQL pre/post correction, exact boundary, non-UTC session, foreign-tenant exclusion, write rejection |
| Parent authority remains single owner | adapter accepts no purpose/authorization input | #155 owns Employment transport isolation; #149 owns Employment authorization/service revalidation; #55 owns canonical People HTTP/runtime contracts |

## Test-first and repair chain

The adapter’s earlier capability-integrity, retained-UUID, transaction-integrity, and real-PostgreSQL contracts remain unchanged. `15c28cfaafd261bdea047961fb5461c641bb8be5` requires exact non-autocommit proof before cursor acquisition, while canonical owner issue #318 carries the same invariant upstream rather than copying child implementation.

Parent reconciliation is ordinary and non-force:

1. `23e2ffb028628d74df7de12196fb8a336b3a68cb` adopted #155’s oversized-path-before-tokenization repair.
2. `04d1c354d2b7bce972af38d26e64c590a70f0550` adopted #155’s first Employment event-loop repair lineage while preserving all #156-owned PostgreSQL files.
3. #155 then corrected support-reference ownership after verifying canonical #55 `_send_json(..., support_reference=...)`; test-first `a38c0b2286aff93ec19a766bcd63927754648e7b` and causal repair `15220135234107de82c481816f19749198c61012` bind the logged and returned opaque reference without duplicating parent emitter logic.
4. `91dc5fb3356297cc60248e049164e33637bb92a3` adopted that corrected #155 transport parent.
5. Canonical People owner issue #320 subsequently proved `PeopleAsgiApp` itself still executed synchronous governed reads on the ASGI event loop. #55 test-first `e1b23b2ad08cb4a1c53adbf1002d6204f37871cc` adds the off-loop contract; causal repair `d9803ae86fbc63bb41197c55d071dbba033361e8` moves `read_worker_people_record(...)` through `asyncio.to_thread(...)` while retaining the short DB transaction in the read port. #149 adopts that owner truth in `afafd9b57e65d25f0586e68272247b2c0afb6e38`; #155 adopts it in `28a0993e84c28edd0fae0e70021aa0c9c1549a07`; #156 adopts the same parent-owned two-file delta in ordinary merge `a446b75f3eb388910e6a31c22f281956dd7cbba8` without modifying PostgreSQL-owned files.

## Evidence interpretation

Python DB-API tests prove adapter capability/input/transaction behavior; they are not described as real PostgreSQL runs. `tests/test_bitemporal_postgres.sh` separately executes production SQL constants against seeded PostgreSQL when canonical Foundation runs and does not claim to exercise psycopg pool behavior. Forced-RLS remains owned by the dedicated tenant-isolation PostgreSQL contract.

Current direct parent authority is #155 `28a0993e84c28edd0fae0e70021aa0c9c1549a07`. The inherited People/Employment HTTP event-loop isolation is parent-owned and is not reimplemented in the PostgreSQL adapter.

Because #156 remains stacked on #155 while canonical Foundation pull-request acceptance targets `develop`, absence of a hosted run is not GREEN. After #55/#65/#149/#155 and prerequisites reach protected `develop`, #156 must ordinary-forward onto protected truth and reacquire exact-head Foundation—including real PostgreSQL and full People coverage—plus Security/SAST/CodeQL/model review and qualifying independent approval.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It performs no authorization, mutation, audit/outbox write, cross-service join, or high-impact employment decision. Transaction scope is bounded to database setup/query/fetch work and never spans authentication or unrelated computation.
