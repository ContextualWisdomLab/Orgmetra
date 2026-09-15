# ADR 0015: Governed Employment separation transition

- Status: Proposed
- Date: 2026-09-12
- Owners: People Core / HRIS
- Related: #314, #302, ADR 0003, ADR 0004, ADR 0005, ADR 0006, ADR 0008

## Problem

Orgmetra already rejects in-place business mutation of `employment_record_version`, so changing `employment_status_code` from `active` or `leave` to `terminated` is intentionally invalid. The People bounded context nevertheless needs an authoritative way to end an Employment before rehire can create a later Employment for the same Person.

Two fields could otherwise become competing termination truths: `effective_to` on a surviving active/leave version and a separate `terminated` status. A separation command also has to survive retries, concurrent submissions, stale version references, tenant confusion, future-scheduled Employment facts, open Assignments, and audit/outbox failure without leaving partial history.

The persistence function is also a high-impact database capability. Revoking PUBLIC execution while leaving it `SECURITY INVOKER` is not a complete runtime boundary: a service principal would need the underlying People and audit/outbox DML rights merely to invoke the function, which would let that principal bypass the governed transition with direct SQL.

A further cross-command race exists if Assignment creation and Employment separation do not share one aggregate conflict boundary. Separation already locks `employment_record` before checking Assignment truth, but an Assignment writer that only reads Employment versions can validate an active version and insert after that check. Conversely, an Assignment read begun before a separation lock is released can retain a READ COMMITTED statement snapshot that predates the newly committed terminal version. The invariant therefore cannot be protected by application-level validation or by adding a row lock to the same version-read statement alone.

## Constraints

- Person identity and prior Employment identity/history must remain immutable.
- Recorded-time history is correction-not-rewrite. A previously known fact remains queryable at its earlier knowledge coordinate.
- Business-effective and recorded-time intervals are half-open.
- A high-impact separation requires explicit actor, purpose, reason, evidence and human confirmation.
- Tenant context must be bound before acquiring database-global advisory coordination state.
- Assignment lifecycle is owned by the Assignment boundary. Separation may not silently rewrite or close Assignment facts.
- Assignment creation and Employment separation must serialize on the same Employment aggregate before either can establish contradictory durable truth.
- Rehire uses a new Employment identity unless a later, separately reviewed contract explicitly establishes another rule.
- The externally assignable separation capability must not carry direct People/audit/outbox table DML or RLS-bypass authority.
- Ordinary Assignment writers must not receive broad Employment UPDATE authority merely to participate in aggregate serialization.

## Considered alternatives

### Rewrite the current Employment version in place

Rejected. It destroys the knowledge-time history already protected by ADR 0003 and by the database mutation guard.

### Use only `effective_to` as the termination fact

Rejected. `effective_to` is an interval boundary and cannot by itself carry the governed terminal state, reason, evidence, confirmation, audit identity, or retry provenance required for a high-impact lifecycle decision.

### Keep the old active/leave version open and append an overlapping `terminated` version

Rejected. Overlapping business intervals would make the current Employment state ambiguous and conflict with the existing bitemporal exclusion contract.

### Let separation update Assignment rows in the same command

Rejected. It crosses aggregate ownership and makes one Employment transaction responsible for Assignment policy and recovery. Open or future-effective Assignments instead cause the separation command to fail closed until their owner coordinates them.

### Validate Assignment coverage only in the application adapter

Rejected. Direct database writers and a concurrent separation can bypass or invalidate a pre-insert application observation. The invariant is relational and must remain correct at the authoritative database boundary.

### Add `FOR UPDATE` to the existing Assignment Employment-version read

Rejected as the sole repair. Under READ COMMITTED, a statement takes its snapshot before it waits for a conflicting row lock. After the wait it can therefore continue from a pre-separation version snapshot. The writer needs a separate Employment-anchor lock statement followed by a fresh coverage read, or an equivalent database-owned boundary.

### Grant the ordinary Assignment writer UPDATE privilege on Employment solely for row locking

Rejected. PostgreSQL requires UPDATE privilege for `SELECT ... FOR UPDATE`; widening the normal writer for a coordination mechanism would enlarge its DML capability without a business mutation need.

### Keep the separation function as SECURITY INVOKER and grant the service its table privileges

Rejected. The application would then hold direct `employment_record_version`, separation/idempotency and audit/outbox mutation capabilities outside the reviewed function contract. Revoking PUBLIC function execution would not prevent bypass of its tenant, replay, evidence and history rules.

### Make the runtime application own the SECURITY DEFINER function

Rejected. A login/runtime identity must not become the privileged function owner. Ownership and invocation are separate capabilities.

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
10. The database execution boundary is capability-separated. `orgmetra_employment_separation_owner` is a dedicated `NOLOGIN`/`NOBYPASSRLS` owner of the `SECURITY DEFINER` function and receives only the reviewed People/audit/outbox privileges needed by that transaction. `orgmetra_employment_separation_executor` is a distinct `NOLOGIN`/`NOBYPASSRLS` role with schema `USAGE` and function `EXECUTE` only. An application login may be granted the executor capability operationally; it must not be granted the owner role or direct table DML as a substitute.
11. The SECURITY DEFINER boundary retains the fixed `pg_catalog, public, pg_temp` search path, explicit tenant-context check and FORCE RLS. Ownership transfer receives `CREATE` on `public` only inside the atomic migration and revokes it before commit.
12. Assignment INSERT and separation share `employment_record` as their conflict boundary. `assignment_employment_coverage_guard` locks the exact Employment anchor first, then performs a separate post-lock read of current recorded Employment versions and allows the Assignment only when an `active` or `leave` interval fully covers the proposed Assignment interval. This makes both commit orders safe: Assignment-first makes separation re-observe and reject the durable Assignment; separation-first makes Assignment re-observe and reject the terminal Employment state.
13. The Assignment guard executes as SECURITY DEFINER under a dedicated `orgmetra_assignment_employment_guard_owner` role that is `NOLOGIN` and `NOBYPASSRLS`. It receives only schema usage, tenant-scoped Employment/version SELECT, `current_tenant_record_id()` execution, and the minimal `employment_record.recorded_from` UPDATE capability PostgreSQL requires for the anchor row lock. The ordinary Assignment writer does not receive this lock privilege. PUBLIC execution is revoked.
14. Historical Assignment facts ending at or before the separation boundary remain legal. The guard prevents contradictory current/future truth; it does not rewrite or erase past Assignment history.

## Data ownership

`employment_record` remains the durable Employment identity. `employment_record_version` remains the bitemporal business-fact history. `employment_separation_record` stores PII-minimized decision provenance linking the prior version, optional continuation version, terminal version, governed decision metadata and audit event. It is append-only, tenant-qualified and protected by forced RLS.

`assignment_record` remains Assignment-owned truth. Migration `0017_assignment_employment_separation_serialization.sql` adds only a database conflict/coverage guard at Assignment INSERT; separation still does not create, close, rewrite or delete Assignment rows.

No cross-service SQL or copied HR truth is introduced. Keyverse remains the identity/policy backend; external workflow, payroll, identity deprovisioning and notification work belongs after the transaction through owned contracts/events.

The separation owner/executor and Assignment guard-owner roles are database capabilities, not HR identities. They do not replace Keyverse authentication/authorization, Person identity, Employment truth or human confirmation.

## Failure and concurrency semantics

A stale expected version, wrong Person/Employment binding, wrong tenant context, semantic idempotency conflict, future Employment version, or Assignment requiring coordination fails before any durable separation state commits. Exact-key concurrent requests serialize on PostgreSQL advisory transaction state and converge on one first result plus replay. Distinct separation requests serialize on the Employment anchor.

Assignment/separation races use the same Employment row lock in both directions. Acceptance requires the blocked backend to expose the winning backend through PostgreSQL's lock graph with a row/transaction lock wait; elapsed time alone is not proof. After the blocker commits, the waiter must re-evaluate current database truth and either proceed consistently or fail closed. A committed Assignment extending through separation must make separation fail; a committed separation must make a conflicting Assignment fail. Durable postconditions must show no loser-side contradictory fact.

Capability migrations fail before project-object elevation if reserved capability role names already exist. This prevents an existing role with undisclosed membership/ACL state from being silently reused as a privileged owner.

## Evidence required before Accepted

- PostgreSQL contract applies migrations through `0017_assignment_employment_separation_serialization.sql` on PostgreSQL 16.
- Current knowledge contains one pre-separation continuation and one terminal version without effective overlap, while an earlier knowledge coordinate still returns the pre-correction active/leave fact.
- Audit event `time` equals the database-owned separation `recorded_at` and audit/outbox/idempotency/separation facts are one-transaction durable.
- Same-key replay returns the first terminal version and timestamp; changed semantics under the key are rejected.
- Cross-tenant, stale-version, future-version and open-Assignment hostile cases fail closed.
- Concurrent exact-key first attempts expose the real PostgreSQL advisory-lock blocker relationship and converge on one durable separation.
- Distinct-key separation attempts expose the shared Employment row/transaction blocker and leave one winner plus one stale-version loser.
- Assignment-first and separation-first interleavings both expose the Employment anchor as the database blocker and converge on exactly one internally consistent outcome; historical Assignment ending at the separation boundary remains accepted.
- PUBLIC and an unrelated `NOLOGIN`/`NOBYPASSRLS` probe cannot execute the separation function.
- The dedicated separation executor can cross the function boundary but has no direct SELECT/INSERT/UPDATE/DELETE/TRUNCATE capability on the governed People/audit/outbox relations.
- The separation function is owned by the dedicated `NOLOGIN`/`NOBYPASSRLS` owner and executes as SECURITY DEFINER while FORCE RLS remains effective under the caller-supplied tenant context.
- The Assignment guard is owned by its dedicated `NOLOGIN`/`NOBYPASSRLS` role, ordinary Assignment runtime authority is not widened for anchor locking, and FORCE RLS still scopes its post-lock Employment coverage read.
- Canonical Foundation owner registers the focused PostgreSQL roots/companions without duplicating workflow ownership and exact-head hosted evidence is green.

Until those conditions are present on the protected stack, this ADR remains Proposed.
