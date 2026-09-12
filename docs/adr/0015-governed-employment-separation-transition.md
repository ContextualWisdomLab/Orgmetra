# ADR 0015: Governed Employment separation transition

- Status: Proposed
- Date: 2026-09-12
- Owners: People Core / HRIS
- Related: #314, #302, ADR 0003, ADR 0004, ADR 0005, ADR 0006, ADR 0008

## Problem

Orgmetra already rejects in-place business mutation of `employment_record_version`, so changing `employment_status_code` from `active` or `leave` to `terminated` is intentionally invalid. The People bounded context nevertheless needs an authoritative way to end an Employment before rehire can create a later Employment for the same Person.

Two fields could otherwise become competing termination truths: `effective_to` on a surviving active/leave version and a separate `terminated` status. A separation command also has to survive retries, concurrent submissions, stale version references, tenant confusion, future-scheduled Employment facts, open Assignments, and audit/outbox failure without leaving partial history.

## Constraints

- Person identity and prior Employment identity/history must remain immutable.
- Recorded-time history is correction-not-rewrite. A previously known fact remains queryable at its earlier knowledge coordinate.
- Business-effective and recorded-time intervals are half-open.
- A high-impact separation requires explicit actor, purpose, reason, evidence and human confirmation.
- Tenant context must be bound before acquiring database-global advisory coordination state.
- Assignment lifecycle is owned by the Assignment boundary. Separation may not silently rewrite or close Assignment facts.
- Rehire uses a new Employment identity unless a later, separately reviewed contract explicitly establishes another rule.

## Considered alternatives

### Rewrite the current Employment version in place

Rejected. It destroys the knowledge-time history already protected by ADR 0003 and by the database mutation guard.

### Use only `effective_to` as the termination fact

Rejected. `effective_to` is an interval boundary and cannot by itself carry the governed terminal state, reason, evidence, confirmation, audit identity, or retry provenance required for a high-impact lifecycle decision.

### Keep the old active/leave version open and append an overlapping `terminated` version

Rejected. Overlapping business intervals would make the current Employment state ambiguous and conflict with the existing bitemporal exclusion contract.

### Let separation update Assignment rows in the same command

Rejected. It crosses aggregate ownership and makes one Employment transaction responsible for Assignment policy and recovery. Open or future-effective Assignments instead cause the separation command to fail closed until their owner coordinates them.

## Decision

A separation is one governed correction of an exact current-known Employment version.

1. The command names tenant, Person, Employment, expected Employment version, separation effective date, controlled separation reason, evidence reference/version, actor, `workforce_admin` purpose, human confirmation and idempotency key.
2. Tenant context is checked before the exact tenant+route+idempotency-key advisory transaction lock.
3. A matching idempotency key replays the first durable result; a changed semantic command under the same key fails closed.
4. The Employment anchor is locked and the exact expected version must still be current in recorded time and `active` or `leave` at the requested effective date.
5. Any other current-known Employment version that would overlap the terminal interval requires explicit future-version coordination rather than implicit cancellation. Any Assignment that would remain effective on or after separation likewise blocks the command.
6. The database reads one post-lock `clock_timestamp()`. The expected version's recorded interval closes at that instant. When the separation date is after the expected version's `effective_from`, a replacement continuation version preserves the pre-separation interval `[effective_from, separation_effective_on)`. A new `terminated` version owns `[separation_effective_on, infinity)`.
7. The continuation `effective_to` is therefore a structural interval boundary, not an independent termination truth. The terminal successor status plus `employment_separation_record` is the authoritative separation fact.
8. The database generates the CloudEvents-compatible `employment_separated` audit envelope from the same command and post-lock timestamp, persists audit/outbox state, append-only separation provenance and the People idempotency binding in the same transaction.
9. Rehire, when implemented under #302, must create a new Employment for the existing Person and cite a successfully separated prior Employment. It must not reopen the terminated Employment or infer authority from an old candidate-worker conversion.

## Data ownership

`employment_record` remains the durable Employment identity. `employment_record_version` remains the bitemporal business-fact history. `employment_separation_record` stores PII-minimized decision provenance linking the prior version, optional continuation version, terminal version, governed decision metadata and audit event. It is append-only, tenant-qualified and protected by forced RLS.

No cross-service SQL or copied HR truth is introduced. Keyverse remains the identity/policy backend; external workflow, payroll, identity deprovisioning and notification work belongs after the transaction through owned contracts/events.

## Failure and concurrency semantics

A stale expected version, wrong Person/Employment binding, wrong tenant context, semantic idempotency conflict, future Employment version, or Assignment requiring coordination fails before any durable separation state commits. Exact-key concurrent requests serialize on PostgreSQL advisory transaction state and converge on one first result plus replay. A test is acceptable only when the second backend is observed waiting on the first through PostgreSQL's lock graph; elapsed time alone is not serialization evidence.

## Evidence required before Accepted

- PostgreSQL contract applies migrations through `0014_employment_separation_transition.sql` on PostgreSQL 16.
- Current knowledge contains one pre-separation continuation and one terminal version without effective overlap, while an earlier knowledge coordinate still returns the pre-correction active/leave fact.
- Audit event `time` equals the database-owned separation `recorded_at` and audit/outbox/idempotency/separation facts are one-transaction durable.
- Same-key replay returns the first terminal version and timestamp; changed semantics under the key are rejected.
- Cross-tenant, stale-version, future-version and open-Assignment hostile cases fail closed.
- Concurrent exact-key first attempts expose the real PostgreSQL advisory-lock blocker relationship and converge on one durable separation.
- Canonical Foundation owner registers the focused PostgreSQL contract without duplicating workflow ownership and exact-head hosted evidence is green.

Until those conditions are present on the protected stack, this ADR remains Proposed.
