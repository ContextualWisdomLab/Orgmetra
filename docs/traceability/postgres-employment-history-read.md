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
| Parent authority remains single owner | adapter accepts no purpose/authorization input | #155 owns Employment transport isolation/scalar integrity; #149 owns Employment authorization/service revalidation; #55 owns canonical People HTTP/runtime contracts |

## Test-first and repair chain

The adapter’s earlier capability-integrity, retained-UUID, transaction-integrity, and real-PostgreSQL contracts remain unchanged. `15c28cfaafd261bdea047961fb5461c641bb8be5` requires exact non-autocommit proof before cursor acquisition, while canonical owner issue #318 carries the same invariant upstream rather than copying child implementation.

Parent reconciliation is ordinary and non-force:

1. `23e2ffb028628d74df7de12196fb8a336b3a68cb` adopted #155’s oversized-path-before-tokenization repair.
2. `04d1c354d2b7bce972af38d26e64c590a70f0550` adopted #155’s first Employment event-loop repair lineage while preserving all #156-owned PostgreSQL files.
3. #155 corrected support-reference ownership after verifying canonical #55 `_send_json(..., support_reference=...)`; `91dc5fb3356297cc60248e049164e33637bb92a3` adopted that corrected transport parent.
4. Canonical People owner #320 moved `read_worker_people_record(...)` through `asyncio.to_thread(...)`; #149/#155/#156 ordinary-forward adopted that owner delta without modifying #156-owned PostgreSQL files.
5. Issue #321 then proved canonical People path/query ingress accepted executable `str`/`bytes` subtypes before authentication. #55 owner-local RED `32585ce837daf01f8fd7e92b71676825674d55bc` and repair `e3c8a1efabdae3da2c33fc75cb27d925e2b60c9b` establish exact built-in scalar authority. #149 adopted it in `5de7207c84cda5f5d8e2f358e379748d95acb9e4`; #155 adopted the owner delta and independently repaired its Employment parser (`a6862f7f...` → `e1618605...`) with ADR/traceability current through `49f5f2542ea0569b0e3b2de8371b7ab88f1b0feb`.
6. #156 first adopted the canonical #55 scalar delta in `cf7abed0baadf62b9f2727489b00aba4b0189641`, then ordinary two-parent merge `2bc8c4250ba3fa6580ec724ebd1d0f673c3ede59` adopted current #155 Employment source/tests/docs. No #156 PostgreSQL source, SQL contract, or transaction test changed in either restack.

## Evidence interpretation

Python DB-API tests prove adapter capability/input/transaction behavior; they are not described as real PostgreSQL runs. `tests/test_bitemporal_postgres.sh` separately executes production SQL constants against seeded PostgreSQL when canonical Foundation runs and does not claim to exercise psycopg pool behavior. Forced-RLS remains owned by the dedicated tenant-isolation PostgreSQL contract.

Current direct parent authority is #155 `49f5f2542ea0569b0e3b2de8371b7ab88f1b0feb`. The inherited People/Employment HTTP event-loop and scalar-integrity controls are parent-owned and are not reimplemented in the PostgreSQL adapter.

Because #156 remains stacked on #155 while canonical Foundation pull-request acceptance targets `develop`, absence of a hosted run is not GREEN. After #55/#65/#149/#155 and prerequisites reach protected `develop`, #156 must ordinary-forward onto protected truth and reacquire exact-head Foundation—including real PostgreSQL and full People coverage—plus Security/SAST/CodeQL/model review and qualifying independent approval.

## Security and data boundary

The adapter reads only Employment anchor identity/Person binding and Employment-version fields. It performs no authorization, mutation, audit/outbox write, cross-service join, or high-impact employment decision. Transaction scope is bounded to database setup/query/fetch work and never spans authentication or unrelated computation.
