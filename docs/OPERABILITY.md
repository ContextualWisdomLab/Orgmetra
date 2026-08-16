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
- `audit_event_record` is immutable evidence. Operations may inspect it but never repair delivery by rewriting its canonical bytes or digest.
- `outbox_delivery_record` is transport state. A dispatcher may move `pending -> leased -> delivered`, return `leased -> pending` with a bounded failure code and cleared lease metadata for retry, atomically replace an expired `leased` ownership grant with a new `leased` grant, or move an exhausted live lease to terminal `dead_lettered`. Delivery identity, audit binding, and stored retry budget never change.
- Delivered and dead-lettered rows are terminal. Redelivery for a new target requires a new target-scoped outbox row; it does not reopen historical delivery state.
- `claim_outbox_delivery(...)` is the only branch-local dispatcher claim contract. It requires the requested tenant to equal the active `orgmetra.tenant_record_id`, a two-or-more-word delivery target, a namespaced opaque worker reference, and a lease duration from 1 through 3600 seconds.
- Claims select due `pending` rows and expired `leased` rows in deterministic availability/record/id order and use PostgreSQL `FOR UPDATE ... SKIP LOCKED` before the guarded update. A successful new claim increments the attempt count once, records the worker, creates a strictly future lease, and returns the immutable canonical event plus digest needed for delivery without copying HR payload fields into mutable transport state.
- A live `leased` row is never claimable. Direct attempts to create an already-expired lease fail closed. When a valid lease later expires, the next claim may atomically take it over, increments the attempt count again, and records `last_failure_code = 'lease_expired'` so worker loss is observable rather than silently stranding work.
- `complete_outbox_delivery(...)` accepts only the active tenant and the exact namespaced owner of a still-live lease. It row-locks the delivery, rejects foreign or expired owners, then atomically clears lease metadata and records terminal `delivered_at`; a stale worker cannot acknowledge work after losing its lease.
- `retry_outbox_delivery(...)` enforces the same live-owner capability boundary, requires a lower `snake_case` failure code and a retry delay from 1 through 86400 seconds, preserves the attempt count, clears lease metadata, and returns the delivery to `pending` no earlier than the bounded retry time.
- `maximum_attempt_count` is durable delivery policy, defaults to 5 on this migration, is constrained to 1 through 100, and is immutable after the delivery row exists. A dispatcher cannot supply or lower that threshold at terminal-failure time.
- `dead_letter_outbox_delivery(...)` is the only supported terminal failure function. It row-locks the delivery, requires the active tenant and exact owner of a still-live lease, reads the stored `maximum_attempt_count`, and rejects dead-lettering until durable `delivery_attempt_count` reaches that budget.
- The database transition guard independently requires exhausted stored budget and matching escalation evidence, so structurally valid direct `leased -> dead_lettered` DML cannot omit those invariants. A deferred binding constraint rejects escalation evidence unless the referenced delivery commits as matching terminal `dead_lettered` state with the same attempt count and failure code.
- A successful dead-letter transition clears lease metadata, preserves the terminal failure code, moves the queue row to `dead_lettered`, and atomically inserts one tenant-scoped `outbox_delivery_escalation_record` with the terminal attempt count and a namespaced opaque escalation reference. The escalation row is append-only and cannot be rewritten to make an operational failure disappear.
- Dead-lettered rows are excluded from normal claiming. Recovery requires an explicit new business/operator action and must not mutate or reopen the terminal historical row.
- Expired owners must recover through `claim_outbox_delivery(...)` before completion, retry, or dead-lettering. This prevents a worker that lost ownership from racing the replacement owner after lease takeover.
- Exponential/backoff policy selection, policy-specific producer configuration, and external delivery receipts remain release blockers before reliable asynchronous delivery is called production-ready; terminal dead-letter/escalation evidence is implemented but does not by itself prove downstream receipt.

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
- Restored data is not serviceable until tenant isolation, temporal interval, append-only trigger, evidence-reference, audit-envelope digest, outbox-state/escalation, and manifest integrity checks pass.

## Incident classes

- authorization verification or revocation failure
- cross-tenant access attempt
- evidence or audit-envelope integrity failure
- outbox lease/retry/dead-letter or delivery-state corruption
- missing or tampered outbox escalation evidence
- integration outage
- bitemporal corruption
- LLM draft hallucination detected
- validation study discrepancy
- migration reconciliation failure
