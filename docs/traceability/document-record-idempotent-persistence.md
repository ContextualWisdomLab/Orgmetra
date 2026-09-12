# Document-record idempotent persistence traceability

Status: active stacked evidence for #309/#312. This file is not protected-`develop` truth until the stack integrates normally.

| Requirement | Owner artifact | Executable evidence | Current state |
| --- | --- | --- | --- |
| One retry family has one tenant-scoped opaque key | `document_record_persist_receipt.idempotency_key` in migration 0024 | invalid/different-key behavior is constrained by the migration; #312 review remains pending | Implemented on Draft head |
| Same key + same semantic command returns the first committed result | `persist_document_record_once(...)` semantic digest + replay branch | `tests/test_document_record_idempotency_postgres.sh` compares first and retry result and proves one `document_record` + one receipt | Implemented; hosted execution pending Foundation admission |
| Same key + changed semantics fails closed | server-side `orgmetra.document_record_persist_command.v1` SHA-256 | PostgreSQL contract changes only `application_evidence_digest_sha256` and requires the explicit semantic-conflict error | Implemented; hosted execution pending |
| Retry identity is independent of caller session timezone | function-local `SET TimeZone = 'UTC'` for digest construction | same semantic command executes first under UTC, then under Asia/Seoul; result/digest identity must remain identical | Implemented; hosted execution pending |
| Unsupported transaction isolation fails closed | `current_setting('transaction_isolation')` guard before command validation/write | `tests/test_document_record_idempotency_isolation_postgres.sh` invokes the owner inside a real `REPEATABLE READ` transaction and requires the explicit isolation error first | Implemented; hosted execution pending |
| Concurrent first attempts serialize | transaction-scoped `pg_advisory_xact_lock` over tenant + owner namespace + key | two real PostgreSQL sessions; first keeps its transaction open after persistence while the second invokes the same command | Implemented; hosted execution pending |
| Replay visibility is explicit | `VOLATILE` function + Read Committed guard | ADR 0309 ties post-lock receipt visibility to PostgreSQL statement snapshots and rejects stronger isolation until a successor algorithm exists | Implemented contract |
| No long external operation is inside the lock | ADR 0309 + database-only function body | source inspection: function performs digesting, replay lookup, local inserts, and receipt derivation only | Implemented; service adapter not yet present |
| Receipt cannot bind to another tenant's document | tenant-qualified UNIQUE on `document_record`; composite FK from receipt | migration DDL plus FORCE-RLS acceptance | Implemented; hosted execution pending |
| Receipt state is append-only | append-only row trigger + TRUNCATE trigger | PostgreSQL contract requires UPDATE rejection; table is FORCE RLS | Implemented; hosted execution pending |
| Replay state is PII-minimized | receipt stores tenant, opaque key, digests, document identity, database time only | schema inspection; no document bytes, free-form HR values, credentials, compensation, rating, or duplicated Person/Employment columns | Implemented |
| Lost-response retry can recover authoritative identity | receipt persists in the same transaction as the document write | first committed result is followed by a separate retry that must return the same stored receipt/result | Implemented; hosted execution pending |
| Acceptance connections are closed | test sessions set dedicated `PGAPPNAME` values and are waited before inspection | `pg_stat_activity` must contain zero matching sessions after concurrent acceptance | Implemented; hosted execution pending |
| Foundation cannot silently omit the new PostgreSQL contracts | #310/#311 owner-neutral discovery | #310 handoff references both document-record idempotency PostgreSQL contracts; no feature-local workflow is added | Dependency pending stack reconciliation |
| Creation/retry receipt is not destruction-completion evidence | ADR 0309 / #308 boundary | #307 dependency order keeps #309/#312 and #308 as distinct prerequisites | Explicitly separated |

## Evidence lineage

- Parent authority: #107 `7ce73aa44f47113b2ecd42d51bb5d38a22c0367d`.
- Initial RED contract: `6260960f2909d34803dad2890f0c0bfd0f7bede7`.
- Initial owner migration/function: `b341784aaabca61dff2663986d24fd5e61b5a1c9`.
- Initial ADR: `3ef61434b04c6cc01d15788a62e71fc8036ad926`.
- First traceability commit: `c3ee1faaa30451e4d31fd959cf4abb77c3bd6a07`.
- PostgreSQL 16 / Read Committed ADR correction: `a2f4490423b97b21b8f94262157f2270cd53226e`.
- Timezone-drift RED: `db8360801ac852f343cebae5fdd592866c091ae7`.
- Function-local UTC causal fix: `00ba4ee03df7ca86bfc3ef2383e04de211532296`.
- Unsupported-isolation RED: `7a5393c279d9ef65f412a01ab891e71e4585c7fd`.
- Read Committed fail-closed causal fix: `bfc26948096e72524c434d22a7f6944e8446334b`.
- ADR currentization for owner-side isolation enforcement: `20dc8c8374c46d445de4ab19b67d3cbd95f527b9`.

## Evidence limits

No hosted PostgreSQL execution is claimed on the current stacked branch. #312 targets #107, while the canonical PostgreSQL Foundation implementation is separately stacked under #259/#311. Exact-head GREEN requires ordinary-forward reconciliation of those histories and a fresh run that discovers both contracts without filename-specific workflow logic.

CodeRabbit/Devin status is review evidence only. It is not a substitute for the PostgreSQL runtime contracts, required protected-branch gates, or a qualifying independent approval.
