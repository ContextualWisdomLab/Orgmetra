# Document-record idempotent persistence traceability

Status: active stacked evidence for #309/#312. This file is not protected-`develop` truth until the stack integrates normally.

| Requirement | Owner artifact | Executable evidence | Current state |
| --- | --- | --- | --- |
| One retry family has one tenant-scoped opaque key | `document_record_persist_receipt.idempotency_key` in migration 0024 | invalid/different-key behavior is constrained by the migration; #312 review remains pending | Implemented on Draft head |
| Same key + same semantic command returns the first committed result | `persist_document_record_once(...)` semantic digest + replay branch | `tests/test_document_record_idempotency_postgres.sh` compares first and retry result bytes and proves one `document_record` + one receipt | Implemented; hosted execution pending Foundation admission |
| Same key + changed semantics fails closed | server-side `orgmetra.document_record_persist_command.v1` SHA-256 | PostgreSQL contract changes only `application_evidence_digest_sha256` and requires the explicit semantic-conflict error | Implemented; hosted execution pending |
| Concurrent first attempts serialize | transaction-scoped `pg_advisory_xact_lock` over tenant + owner namespace + key | two real PostgreSQL sessions; first keeps its transaction open after persistence while the second invokes the same command | Implemented; hosted execution pending |
| No long external operation is inside the lock | ADR 0309 + database-only function body | source inspection: function performs digesting, replay lookup, local inserts, and receipt derivation only | Implemented; service adapter not yet present |
| Receipt cannot bind to another tenant's document | tenant-qualified UNIQUE on `document_record`; composite FK from receipt | migration DDL plus FORCE-RLS acceptance | Implemented; hosted execution pending |
| Receipt state is append-only | append-only row trigger + TRUNCATE trigger | PostgreSQL contract requires UPDATE rejection; table is FORCE RLS | Implemented; hosted execution pending |
| Replay state is PII-minimized | receipt stores tenant, opaque key, digests, document identity, database time only | schema inspection; no document bytes, free-form HR values, credentials, compensation, rating, or duplicated Person/Employment columns | Implemented |
| Lost-response retry can recover authoritative identity | receipt persists in the same transaction as the document write | first result is intentionally ignored by the retry assertion; retry must return the same stored receipt/result | Implemented; hosted execution pending |
| Acceptance connections are closed | test sessions set dedicated `PGAPPNAME` values and are waited before inspection | `pg_stat_activity` must contain zero matching sessions after concurrent acceptance | Implemented; hosted execution pending |
| Foundation cannot silently omit the new PostgreSQL contract | #310/#311 owner-neutral discovery | #310 handoff references `tests/test_document_record_idempotency_postgres.sh`; no feature-local workflow is added | Dependency pending stack reconciliation |
| Creation/retry receipt is not destruction-completion evidence | ADR 0309 / #308 boundary | #307 dependency order keeps #309/#312 and #308 as distinct prerequisites | Explicitly separated |

## Evidence lineage

- Parent authority: #107 `7ce73aa44f47113b2ecd42d51bb5d38a22c0367d`.
- RED contract: `6260960f2909d34803dad2890f0c0bfd0f7bede7`.
- Owner migration/function: `b341784aaabca61dff2663986d24fd5e61b5a1c9`.
- ADR 0309: `3ef61434b04c6cc01d15788a62e71fc8036ad926`.
- This traceability update follows those artifacts and must be re-keyed to the final #312 exact head before merge.

## Evidence limits

No hosted PostgreSQL execution is claimed on the current stacked branch. #312 targets #107, while the canonical PostgreSQL Foundation implementation is separately stacked under #259/#311. Exact-head GREEN requires ordinary-forward reconciliation of those histories and a fresh run that discovers this contract without filename-specific workflow logic.

CodeRabbit/Devin status is review evidence only. It is not a substitute for the PostgreSQL runtime contract, required protected-branch gates, or a qualifying independent approval.
