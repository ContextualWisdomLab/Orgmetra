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
| Parent authority remains single owner | adapter accepts no purpose/authorization input | #155 owns transport/event-loop isolation; #149 owns authorization/service revalidation |

## Test-first and repair chain

The adapter’s earlier test-first, capability-integrity, retained-UUID, transaction-integrity, and real-PostgreSQL contracts remain unchanged. In particular, `15c28cfaafd261bdea047961fb5461c641bb8be5` requires exact non-autocommit proof before cursor acquisition, while canonical owner issue #318 carries the same invariant upstream instead of copying child implementation.

HTTP parent reconciliation proceeded in three ordinary, non-force stages:

1. `23e2ffb028628d74df7de12196fb8a336b3a68cb` adopted #155’s oversized-path-before-tokenization repair.
2. `04d1c354d2b7bce972af38d26e64c590a70f0550` adopted the first event-loop repair lineage from #155 while preserving every #156-owned PostgreSQL file.
3. Fresh owner verification then showed that #155 inherits canonical #55 `_send_json(..., support_reference=...)`; the #154 support-reference signature defect therefore did not apply to #155. #155 corrected its correlation contract through test-first `a38c0b2286aff93ec19a766bcd63927754648e7b`, causal source repair `15220135234107de82c481816f19749198c61012`, ADR `06390b0d5bc14fdd620ba6f83d3a7973bf0ed9a9`, and traceability `2f63f84edb17db5435907e095abf284addcdd2a0`.
4. Ordinary two-parent merge `91dc5fb3356297cc60248e049164e33637bb92a3` adopts that corrected #155 parent. The resolved tree takes exactly the four parent-owned Employment HTTP source/test/ADR/traceability files from #155 and leaves #156-owned PostgreSQL capability, transaction, SQL, and real-database contracts unchanged.

## Evidence interpretation

Python DB-API tests prove adapter capability/input/transaction behavior; they are not described as real PostgreSQL runs. `tests/test_bitemporal_postgres.sh` separately executes the production SQL constants against seeded PostgreSQL when canonical Foundation runs; it does not claim to exercise psycopg pool behavior. Forced-RLS remains owned by the repository’s dedicated tenant-isolation PostgreSQL contract.

Current direct parent authority is #155 `2f63f84edb17db5435907e095abf284addcdd2a0`. #156 is an ordinary descendant through merge `91dc5fb3356297cc60248e049164e33637bb92a3`; inherited HTTP parser bounds, support-reference correlation, and event-loop isolation remain parent-owned and are not reimplemented in the PostgreSQL adapter.

Because #156 is intentionally stacked on #155 while canonical Foundation pull-request acceptance targets `develop`, absence of a hosted run is not GREEN. After #55/#65/#149/#155 and prerequisites reach protected `develop`, #156 must ordinary-forward onto protected truth and reacquire exact-head Foundation—including real PostgreSQL and full People coverage—plus Security/SAST/CodeQL/model review and qualifying independent approval.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It performs no authorization, mutation, audit/outbox write, cross-service join, or high-impact employment decision. Transaction scope is bounded to database setup/query/fetch work and never spans authentication or unrelated computation.
