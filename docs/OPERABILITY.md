# Operability

## SLO candidates

- HRIS core read availability: 99.9% for production deployments.
- High-impact command audit append success: 99.99% within accepted maintenance windows.
- Integration adapter error visibility: every failed outbound command produces an operator-safe event.

## Degraded modes

### Keyverse unavailable

- An already authenticated session may perform only low-risk, non-PII reads for at most 15 minutes after its last successfully verified authorization snapshot.
- The 15-minute authorization lifetime is a hard upper bound. It cannot be renewed from a cached token, local clock extension, or an unavailable Keyverse response.
- PII reads, exports, role changes, identity provisioning, identity deprovisioning, and every high-risk command fail closed whenever current authorization cannot be verified.
- New sessions, new grants, and privilege elevation are rejected.
- Revocation and deprovisioning requests are durably queued with idempotency keys, but the affected subject is denied Orgmetra access immediately until Keyverse confirms completion.
- Every denied or deferred action records an `authorization_verification_unavailable` audit event with tenant, actor, purpose, resource, policy-snapshot time, and correlation reference.
- Recovery requires a fresh Keyverse verification before a session regains PII or mutation capability; queued revocation and deprovisioning commands are reconciled before normal provisioning resumes.

### Audit/outbox persistence

- An accepted business mutation that requires audit evidence must call `record_audit_outbox_event(...)` inside the same PostgreSQL transaction as the authoritative write. A failure to append the audit/outbox pair is a business-transaction failure, not a warning-only condition.
- `audit_event_record` is immutable evidence. Operations may inspect it but never repair delivery by rewriting its canonical bytes or digest. Update/delete and statement-level TRUNCATE are rejected.
- `outbox_delivery_record` is transport state. A dispatcher may move `pending -> leased -> delivered`, return `leased -> pending` with a bounded failure code and cleared lease metadata for retry before exhaustion, atomically replace an expired `leased` ownership grant with a new `leased` grant while attempts remain, or move an exhausted recorded ownership grant to terminal `dead_lettered`. Delivery identity, audit binding, and stored retry budget never change; bulk TRUNCATE is rejected.
- Delivered and dead-lettered rows are terminal. Redelivery for a new target requires a new target-scoped outbox row; it does not reopen historical delivery state.
- The Organization hierarchy application boundary writes the reviewed bitemporal successor, immutable application evidence, and audit/outbox pair in one transaction. A stale snapshot, concurrent hierarchy fact, or effective-time graph conflict fails closed; callers must retry a `40001` result from a fresh transaction and must not replay only the audit or outbox step.
- `claim_outbox_delivery(...)` is the only branch-local dispatcher claim contract. It requires the requested tenant to equal the active `orgmetra.tenant_record_id`, a two-or-more-word delivery target, a namespaced opaque worker reference, and a lease duration from 1 through 3600 seconds.
- Claims select due `pending` rows and expired `leased` rows in deterministic availability/record/id order, use the partial `outbox_delivery_due_work_index`, and take PostgreSQL `FOR UPDATE ... SKIP LOCKED` locks before the guarded update. A successful new claim increments the attempt count once, records the worker, creates a strictly future lease, and returns the immutable canonical event plus digest needed for delivery without copying HR payload fields into mutable transport state.
- Migration 0008 builds `outbox_delivery_due_work_index` with `CREATE INDEX CONCURRENTLY` so an established queue can continue accepting inserts, updates, and deletes during the build. Because PostgreSQL forbids concurrent index creation inside an explicit transaction block, deployment runners must execute that migration in autocommit/non-transactional mode at the index step and treat any invalid concurrent-index residue as a failed migration requiring operator inspection before retry. The hardening DDL before the index and the privileged recovery-role handoff after the index each run in their own explicit transaction.
- Migration 0028 builds the four Organization stale-transaction probe indexes with `CREATE INDEX CONCURRENTLY` and is deliberately retryable after an interrupted build. It must run through `psql` or a migration runner that provides equivalent `\gexec` semantics with autocommit enabled; wrapping the migration in an explicit transaction is unsupported. Before rebuilding, the migration reads `pg_index.indisvalid`, drops only invalid same-named residue with `DROP INDEX CONCURRENTLY`, preserves already-valid indexes, and then uses `CREATE INDEX CONCURRENTLY IF NOT EXISTS` before installing or refreshing the stale-transaction function and trigger. After cancellation or failure, rerun the whole migration from a fresh autocommit session rather than editing catalog state manually. Recovery is complete only when all four named indexes report `indisvalid = true`, `reject_stale_organization_hierarchy_transaction()` exists with the trusted search path, and `organization_hierarchy_application_concurrency_guard` is installed on the application-evidence table.
- A live `leased` row is never claimable. Direct attempts to create an already-expired lease fail closed. Before `maximum_attempt_count` is reached, an expired lease may be atomically taken over, increments the attempt count, and records `last_failure_code = 'lease_expired'`. Once the budget is exhausted, neither pending retry nor expired-lease takeover may create attempt N+1.
- `complete_outbox_delivery(...)` accepts only the active tenant and the exact namespaced owner of a still-live lease. It row-locks the delivery, rejects foreign or expired owners, then atomically clears lease metadata and records terminal `delivered_at`; a stale worker cannot acknowledge work after losing its lease.
- `retry_outbox_delivery(...)` enforces the same live-owner capability boundary, requires a lower `snake_case` failure code and a retry delay from 1 through 86400 seconds, preserves the attempt count, clears lease metadata, and returns the delivery to `pending` no earlier than the bounded retry time. It fails closed once the stored attempt budget is exhausted.
- `maximum_attempt_count` is durable delivery policy, defaults to 5 on this migration sequence, is constrained to 1 through 100, and is immutable after the delivery row exists. A dispatcher cannot supply or lower that threshold at terminal-failure time.
- `dead_letter_outbox_delivery(...)` is the normal worker terminal-failure function. It row-locks the delivery, requires the active tenant and exact recorded owner, reads the stored `maximum_attempt_count`, and rejects dead-lettering until durable `delivery_attempt_count` reaches that budget. The exact recorded stable worker reference may terminalize its expired final lease without creating attempt N+1; a foreign worker cannot use this normal path.
- If the recorded final worker identity is permanently unavailable, `operator_dead_letter_expired_outbox_delivery(...)` provides a separate privileged recovery boundary. It requires exact tenant context, operational UUIDs, an opaque namespaced operator reference, a lower `snake_case` failure code, an already-expired `leased` row, and exhausted stored attempt budget. It row-locks the delivery, appends `outbox_delivery_escalation_record` evidence carrying the operator reference and terminal attempt count, then terminalizes through the existing transition guard.
- Operator recovery uses two service-owned NOLOGIN roles. Migration 0008 fails before changing project objects if either reserved role name already exists; it never reuses a role whose prior memberships or ACLs are unknown. `orgmetra_outbox_recovery_owner` owns the single `SECURITY DEFINER` recovery function, is explicitly `NOBYPASSRLS`, loses schema `CREATE` in the same post-index transaction that performs the ownership handoff, and receives only the transport-table privileges required by that function. `orgmetra_outbox_operator` receives only schema usage and EXECUTE on the recovery function, with no direct outbox SELECT/UPDATE or escalation INSERT privilege. Production login identities obtain this capability only through explicit purpose-bound membership provisioning; migration execution therefore requires cluster authority to create these fresh service-owned roles and must stop for operator review on a role-name collision.
- The database transition guard independently requires exhausted stored budget and matching escalation evidence, so structurally valid direct `leased -> dead_lettered` DML cannot omit those invariants. A deferred binding constraint rejects escalation evidence unless the referenced delivery commits as matching terminal `dead_lettered` state with the same attempt count and failure code; operator recovery forces its pending binding check while the narrowly privileged function owner is still active, then restores deferred mode before returning to the caller.
- A successful dead-letter transition clears lease metadata, preserves the terminal failure code, moves the queue row to `dead_lettered`, and records tenant-scoped immutable escalation evidence. The escalation row is append-only and cannot be rewritten to make an operational failure disappear.
- Dead-lettered rows are excluded from normal claiming. Recovery requires an explicit new business/operator action and must not mutate or reopen the terminal historical row.
- Stable dispatcher worker references remain operational identities. The operator path exists only for the narrower expired-and-exhausted failure mode and does not permit takeover of live or retryable work.
- Audit/outbox SQL boundaries pin `search_path` to `pg_catalog, public, pg_temp`, the migration revokes `CREATE` on `public` from `PUBLIC`, and project objects remain in the trusted application schema until schema extraction work explicitly moves them. Normal dispatcher/persistence functions remain security-invoker boundaries; the lost-final-worker recovery function is the sole `SECURITY DEFINER` exception and is owned by the hardened NOLOGIN recovery role rather than a login or superuser role.
- Exponential/backoff policy selection, policy-specific producer configuration, and external delivery receipts remain release blockers before reliable asynchronous delivery is called production-ready; terminal dead-letter/escalation evidence and lost-final-worker recovery are implemented but do not by themselves prove downstream receipt.

### Other dependencies

- Psychometrics Commons unavailable: assessment-result fetches show an unavailable state, not invented scores.
- TEPP unavailable: temporal analyses remain unavailable; authoritative HRIS facts remain readable under normal authorization.
- Contextual Orchestrator unavailable: AI drafting is disabled; manual workflows continue.
- Semantic Data Portal unavailable: ontology enrichment is disabled; approved job profiles continue.

## Backups

- HRIS PostgreSQL requires encrypted backups, point-in-time recovery, and restore rehearsals.
- Audit/provenance records require immutability and tamper evidence; restored audit rows must recompute to their stored SHA-256 digests before they are treated as review evidence.
- Outbox delivery state and escalation evidence must be restored together with the corresponding audit records. Recovery may retry non-terminal work but must not mutate or reopen a terminal delivered/dead-lettered record or invent a successful delivery receipt.
- Object-store artifacts require tenant-scoped retention and deletion policy.
- Restored data is not serviceable until tenant isolation, temporal interval, append-only/TRUNCATE guards, evidence-reference, audit-envelope digest, outbox-state/escalation, trusted search-path, and manifest integrity checks pass.

## Incident classes

- authorization verification or revocation failure
- cross-tenant access attempt
- evidence or audit-envelope integrity failure
- outbox lease/retry/dead-letter or delivery-state corruption
- missing or tampered outbox escalation evidence
- lost final-attempt dispatcher identity requiring audited operator recovery
- integration outage
- bitemporal corruption
- LLM draft hallucination detected
- validation study discrepancy
- migration reconciliation failure
