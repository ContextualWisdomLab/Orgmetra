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
- `outbox_delivery_record` is transport state. A dispatcher may only move `pending -> leased -> delivered`, or return `leased -> pending` with a bounded failure code and cleared lease metadata for retry.
- A delivered row is terminal. Redelivery for a new target requires a new target-scoped outbox row; it does not reopen historical delivery state.
- This stacked slice does not yet implement production dispatcher claiming, bounded exponential backoff, lease-expiry recovery, dead-letter/escalation policy, or external delivery receipts. Those controls are release blockers for claiming reliable asynchronous audit delivery.
- A production dispatcher must claim work with concurrency-safe row locking and prove crash/restart behavior so two workers cannot both own the same pending delivery and an expired lease is recoverable without losing or mutating the underlying audit fact.

### Other dependencies

- Psychometrics Commons unavailable: assessment-result fetches show an unavailable state, not invented scores.
- TEPP unavailable: temporal analyses remain unavailable; authoritative HRIS facts remain readable under normal authorization.
- Contextual Orchestrator unavailable: AI drafting is disabled; manual workflows continue.
- Semantic Data Portal unavailable: ontology enrichment is disabled; approved job profiles continue.

## Backups

- HRIS PostgreSQL requires encrypted backups, point-in-time recovery, and restore rehearsals.
- Audit/provenance records require immutability and tamper evidence; restored audit rows must recompute to their stored SHA-256 digests before they are treated as review evidence.
- Outbox delivery state must be restored together with the corresponding audit records. Recovery may retry non-terminal work but must not mutate a terminal delivered record or invent a successful delivery receipt.
- Object-store artifacts require tenant-scoped retention and deletion policy.
- Restored data is not serviceable until tenant isolation, temporal interval, append-only trigger, evidence-reference, audit-envelope digest, outbox-state, and manifest integrity checks pass.

## Incident classes

- authorization verification or revocation failure
- cross-tenant access attempt
- evidence or audit-envelope integrity failure
- outbox lease/retry or delivery-state corruption
- integration outage
- bitemporal corruption
- LLM draft hallucination detected
- validation study discrepancy
- migration reconciliation failure
