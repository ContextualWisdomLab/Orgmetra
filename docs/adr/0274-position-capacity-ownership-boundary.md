# ADR 0274: Separate Position ownership with a fenced capacity protocol

## Status

Proposed — active PR only. This ADR is not protected `develop` truth and does not authorize source extraction until the prerequisite owner stack is normally integrated and the distributed invariant has executable evidence.

## Context

Protected `ARCHITECTURE.md` and `docs/TRD.md` assign Position truth to `organization_core` while `people_core` owns Person, Employment, and Assignment. The executable protected tree does not yet have an `organization_core` service owner; the shipped People mutation boundary still creates Position and serializes Assignment capacity against the Position root. Issue #274 tracks this accepted-architecture versus executable-owner gap.

ADR 0004 already makes `position_record` a durable anchor with bitemporal versions and binds Assignment to Employment, Person, and Position. ADR 0005 already requires Assignment days to be covered by an `active` or `open` Position version and visible allocation for one Position seat to remain at or below `1.0000`. This ADR preserves those semantics. It decides only how Position write/capacity authority can move to `organization_core` without adding cross-service SQL, a second Position writer, or a checked-versus-used race.

PostgreSQL 18 `READ COMMITTED` gives each command a new committed snapshot. A read-only availability check followed by a separate People write therefore does not, by itself, preserve the cross-row seat invariant. PostgreSQL row locks can serialize writers inside one database owner, but service extraction requires an explicit cross-context protocol rather than assuming one local transaction.

A second distributed race exists after a capacity debit is fenced. A point-in-time People read that currently finds no Assignment is not proof that a delayed or in-flight `create_assignment` operation cannot commit later. Releasing capacity from that observation can therefore re-open the seat before the original Assignment commits. Post-fence release needs a terminal People-owned attempt outcome that also fences every later commit for the same attempt.

A third race exists if Position eligibility is treated as a mutable read after the capacity fence. An authentic fence issued while Position version V1 is `active|open` cannot remain safe if Organization may independently commit an overlapping `closed`/otherwise-ineligible Position version before People commits Assignment. A People-side recheck does not solve this because Position can change again after the recheck. The Organization reservation therefore has to fence both seat capacity and the Position eligibility required by ADR 0005 for the reservation interval.

A separate operability and correctness hazard appears if the Organization transaction tries to solve those races by calling People while holding the Position row lock. PostgreSQL row locks last until transaction end; a remote call under that lock couples database lock lifetime to network/provider latency, enlarges deadlock and pool-exhaustion surfaces, and turns a local aggregate transaction into an implicit distributed lock. Cross-context coordination must therefore occur outside the Position-locking transaction. The local transaction may accept, fence, confirm, release, or reject from already durable evidence; it may not wait on People while the Position lock is held.

## Decision drivers

The design must:

- keep Position and Position capacity as Organization-domain truth while keeping Assignment history as People-domain truth;
- preserve the bitemporal and allocation semantics already Accepted in ADR 0004/0005;
- expose one canonical capacity writer and no cross-service application-table access;
- remain correct under concurrent claims, retries, delayed requests, process loss, message loss/duplication/reordering, ambiguous timeouts, and concurrent Position status/version mutation;
- bind idempotency to semantic intent rather than a caller-controlled key alone;
- distinguish a terminal abort fence from a point-in-time absence observation;
- make a post-fence receipt durable evidence of both consumed capacity and Position eligibility for its effective interval, rather than requiring an unsafe People-side mutable recheck;
- keep remote service I/O outside Position-root database transactions and row-lock lifetimes;
- minimize PII at the Organization boundary; and
- support a fenced cutover from the existing same-database People mutation path without a dual-writer interval.

## Alternatives

### A. Move Position and Assignment into one Organization aggregate/service

This gives the simplest local transaction for seat allocation, but it moves worker Assignment history out of the protected `people_core` ownership model and couples employment-lifecycle truth to structural Organization ownership. Reject for now.

### B. Keep Position in Organization and call a synchronous availability read before People writes Assignment

This preserves nominal ownership but is not sufficient for correctness. Between availability read and Assignment commit, another writer can consume the same capacity or change Position eligibility. Reject as a TOCTOU design.

### C. Organization-owned `PositionCapacityReservation` with a commit fence and People-owned terminal attempt outcome

Provisionally selected. `organization_core` is the sole writer for Position status/version and Position capacity. `people_core` remains the sole writer for Assignment history and for the terminal outcome of one capacity-authorized Assignment attempt. Their shared invariant is represented by a versioned protocol rather than cross-service SQL.

### D. Two-phase Assignment visibility

People first stores an Assignment in a non-active `pending_capacity` state, Organization confirms capacity, and People then activates it. This avoids a non-expiring unresolved capacity debit but adds another authoritative Assignment lifecycle state plus activation/reconciliation failure windows. Keep as the principal alternative until option C has executable failure evidence; do not mark this ADR Accepted merely because option C is currently preferred.

## Domain model and ubiquitous language

`organization_core` owns:

- `Position`: aggregate root for one tenant-qualified staffable seat and its bitemporal status/version evidence.
- `PositionCapacityReservation`: entity under the Position capacity authority. It binds an opaque reservation identifier, tenant, Position, allocation ratio, effective interval, opaque `assignment_attempt_id`, assignment intent/reference, exact Position version/eligibility evidence, idempotency key, semantic command digest, lifecycle state, and immutable audit/outbox correlation.
- `AllocationRatio` and `EffectiveInterval`: value objects used to calculate overlapping capacity.

`people_core` owns:

- `Assignment`: employment-history fact bound to tenant, Employment, Person, Position, allocation, effective interval, and the exact Organization capacity/eligibility receipt that authorized the write.
- `AssignmentAttemptOutcome`: terminal, tenant-qualified protocol evidence for one opaque `assignment_attempt_id` and exact reservation version/digest. Its terminal state is `committed` with the authoritative Assignment receipt or `aborted` with an immutable abort tombstone. A terminal `aborted` outcome fences every later create/retry for that same attempt from committing an Assignment.

No Person name, compensation, rating, assessment result, or other worker payload is copied into `PositionCapacityReservation`. The cross-context protocol carries only opaque references, semantic digests, version/eligibility evidence, and terminal receipts required to enforce the seat invariant.

## Capacity and Position-eligibility invariants

While a reservation is effective, `held`, `commit_fenced`, and `confirmed` states consume capacity. `released`, `expired`, and `cancelled` states do not. Only `held` may expire autonomously.

For every tenant-qualified Position and every overlapping valid-time slice:

`sum(allocation_ratio for effective held + commit_fenced + confirmed reservations) <= 1.0000`

Every effective `commit_fenced` or `confirmed` reservation also requires Organization-owned Position state to remain assignment-eligible (`active|open` under ADR 0005) for the reservation interval. A Position mutation that would make an effective slice ineligible while such a debit exists cannot commit as an unrelated independent change.

`organization_core` enforces both rules by serializing reservation and Position-status/version mutations at the stable Position root and re-reading the authoritative overlapping debit and Position-version sets inside that local transaction. A stale read model is never capacity or eligibility authority, and the Position-root transaction never performs People/network I/O.

## Protocol

1. `reserve`: under Position-root serialization, validate Position status/version and capacity, then create `held`. The reservation binds one opaque `assignment_attempt_id`. Exact replay of the same idempotency key and semantic digest returns the same reservation; the same key with a different digest fails closed.
2. `arm_commit_fence`: under the same Position-root authority, revalidate capacity and `active|open` coverage for the exact effective interval, then convert `held` to `commit_fenced`. This is durable, idempotent, version-bound, non-expiring, and becomes an Organization promise not to commit an incompatible Position-status/version transition for that interval while the debit remains `commit_fenced` or `confirmed`.
3. `create_assignment`: after the Organization transaction has completed, People accepts only an authentic published/versioned Organization receipt proving the exact reservation is `commit_fenced` for the same tenant, Position, allocation, effective interval, semantic intent, Position eligibility evidence, and `assignment_attempt_id`. People does not perform a second mutable Position availability/status read as correctness authority. Inside one People transaction, it serializes the attempt identity and either writes the Assignment plus terminal `AssignmentAttemptOutcome=committed` atomically, returns the existing equivalent terminal outcome, or fails closed on contradictory evidence. A previously terminal `aborted` attempt can never later commit.
4. `terminalize_attempt`: reconciliation may ask People to resolve the exact attempt. People serializes on `assignment_attempt_id`; if the Assignment already committed, it returns the terminal `committed` outcome. Otherwise it writes a durable terminal `aborted` tombstone that prevents every delayed or retried `create_assignment` for that attempt from committing. A point-in-time `not found`, empty result, HTTP timeout, or missing event is not a terminal outcome.
5. `confirm`: in a new Organization transaction, Organization converts the `commit_fenced` debit to `confirmed` only from the already-obtained terminal People `committed` receipt for the exact attempt/reservation/version/digest. Duplicate or reordered confirmation is idempotent when equivalent and fails closed when contradictory. The Organization transaction does not call People while holding the Position lock.
6. `release`/`adjust`: an ordinary `held` reservation may be released or expire before a commit fence. A `commit_fenced` debit may return capacity only from an already-obtained terminal People `aborted` receipt for the exact attempt, or after a later governed Assignment correction/end makes the debit no longer effective. Timeout, elapsed time, one missing event, one stale read, or present-time Assignment absence is never release authority. Applying the durable receipt is a local Organization transaction; obtaining that receipt happens outside the Position lock.
7. `change_position_status_or_version`: Organization serializes the proposed mutation at the same Position root. If the change would remove `active|open` coverage from an interval consumed by `commit_fenced` or `confirmed` reservations, this transaction fails closed with durable conflict/audit evidence and ends without making a People call. A separate governed workflow may then terminalize/correct affected People attempts/Assignments outside any Position lock, apply resulting terminal receipts to Organization in new local transactions, and retry the exact status/version command against the new Position/reservation version. It cannot invalidate an outstanding fence and leave People holding a stale-but-authentic receipt.

A timeout may enqueue reconciliation; it may not undo a commit fence. No remote timeout extends a Position database lock because cross-context calls are never made from the Position-locking transaction.

## Failure and recovery semantics

- Crash after `held` but before commit fence: bounded expiry may reclaim capacity.
- Crash after commit fence before People receives or commits the create: capacity and Position eligibility stay fenced. Reconciliation may terminalize the attempt, but capacity/eligibility are released only after People durably records `aborted` and thereby fences all future commits for that attempt.
- Delayed/in-flight `create_assignment` racing `terminalize_attempt`: People serializes both by `assignment_attempt_id`, so exactly one terminal outcome wins. If `committed` wins, Organization must confirm and cannot release; if `aborted` wins, the delayed create must replay/fail as aborted and cannot commit.
- Position status/version mutation racing a fenced Assignment attempt: the local Organization mutation serializes against the same Position root and live reservation set. If the proposed change would make the fenced/confirmed effective slice ineligible, it exits with conflict rather than calling People under the lock. Separate orchestration resolves People state, applies receipts locally, then retries. People never relies on a check-then-write status query to repair this race.
- Crash during that external coordination: the original Position state/fence remains authoritative because the rejected Organization transaction made no eligibility change. Idempotent People terminalization/correction and Organization receipt application can resume without holding a distributed lock.
- Crash after People commits Assignment plus terminal `committed` outcome but before Organization receives `confirm`: capacity and Position eligibility stay fenced; a second overlapping claim that would exceed `1.0000` is rejected. Reconciliation confirms from authoritative People evidence.
- Lost, duplicated, or reordered confirm/release messages: attempt/reservation version and semantic-digest-bound idempotency preserves one outcome or fails closed on contradiction.
- Reconciliation records its evidence and decision in immutable audit/outbox data. It cannot infer terminal absence from time, request delivery state, or a current read that finds no Assignment.

This is a Saga-style compensating protocol, not a distributed ACID claim. Compensations are explicit domain transitions with evidence; retries, TTLs, present-time absence, transport observations, and a network call made while holding a database row lock are not substitutes for atomicity or terminal-outcome evidence.

## Cutover and rollback

Extraction must not create two Position/capacity writers.

1. Integrate #64 normally so the currently shipped People mutation/concurrency truth is protected.
2. Integrate #96 and then #119 through their canonical Organization stack; descendants adopt protected predecessors with ordinary non-force history.
3. Implement and test the Organization owner and published/versioned capacity contract while this ADR remains Proposed.
4. Before authority switch, fence new Assignment capacity mutations.
5. Project current and future-effective Assignment occupancy into the Organization reservation ledger. Bind the projection to an immutable migration manifest/digest and verify tenant, Position, effective interval, allocation, Position eligibility, and aggregate-sum equivalence.
6. Switch Position/capacity write authority to `organization_core`, then switch `people_core` to the published capacity/attempt protocol, then remove the fence.

Rollback must be defined and rehearsed before un-fencing. It must select one writer authority; it must never re-enable both the legacy People Position/capacity writer and the Organization writer.

## Acceptance before Accepted status

This ADR may move from Proposed only after the owner stack has executable evidence for all of the following on the exact candidate head:

- two concurrent `0.6000` reservations for one Position and overlapping interval: exactly one succeeds;
- non-overlapping future intervals can both succeed when their own slices remain within capacity;
- exact replay versus same-key/different-digest behavior;
- crash after `held` before commit fence and bounded expiry;
- crash after commit fence before People commit with no release from mere absence;
- a deliberately delayed `create_assignment` racing attempt terminalization: exactly one terminal People outcome (`committed` or `aborted`) wins, `aborted` fences the late create, and `committed` prevents Organization release;
- a Position close/status-version change racing a fenced create: the Organization mutation cannot make the reservation interval ineligible while People can still commit from the authentic fence receipt;
- instrumentation/probes showing Position-root database transactions perform no People/network I/O and remote latency cannot extend the Position row-lock lifetime;
- crash during external Position-change coordination with the original Position eligibility/fence remaining authoritative and idempotent recovery succeeding;
- crash after Assignment commit before confirm with capacity and Position eligibility remaining fenced;
- lost/duplicated/out-of-order confirm/release messages with version/digest-bound idempotency;
- Assignment correction/end and capacity/eligibility adjustment without leakage, overbooking, or an Assignment visible outside `active|open` Position coverage;
- migration projection equivalence and rollback rehearsal without a dual-writer interval;
- real two-service/PostgreSQL interleavings proving no effective slice exposes allocation above `1.0000`, no Assignment write is authorized outside its fenced Position eligibility, and no cross-service SQL exists;
- connection/resource cleanup and immutable audit/outbox evidence for failures as well as success; and
- buyer-path reserve/fence/create/terminalize/confirm/release plus conflicting Position-change measurements at p95 <= 20 ms under real concurrency without sample shrinking, excluded slow paths, or warm-cache-only evidence.

Synthetic fixtures may prove deterministic mechanism behavior. Buyer-realistic or scientific claims require provenance-backed right-cleared data.

## Consequences

- Position ownership can match the accepted context map without moving worker Assignment history into Organization.
- Capacity and Position eligibility become explicit Organization domain authority rather than implicit People SQL reads.
- A post-fence debit can no longer be released merely because People currently shows no Assignment; release requires a terminal People abort tombstone that also prevents a delayed commit for the same attempt.
- Organization also cannot independently close or otherwise invalidate the fenced effective slice while People can still commit from the authentic receipt; the same Position-root serialization governs capacity debits and eligibility-changing Position mutations.
- Cross-context coordination is deliberately not performed under the Position row lock. Conflicting status/version commands fail closed locally, external orchestration resolves People evidence, and a later local Organization transaction applies the result and retries against exact version/digest evidence.
- Ambiguous post-fence failures fail closed as capacity/eligibility reservation until an explicit terminal attempt outcome exists, preferring temporary under-utilization over durable overbooking or invalid Assignment coverage.
- The protocol adds reservation state, a People attempt-outcome fence, Position eligibility fencing, reconciliation, and operational evidence that a single local transaction does not require; that cost is accepted only if executable evidence confirms the bounded-context separation remains worthwhile.
- ADR 0004/0005 remain Accepted semantic authority. This ADR amends only the future service-ownership/consistency mechanism after successful extraction evidence.

## References

See `docs/doctoring/position-capacity-reservation-references.md` for APA 7th records and design mapping. The primary design inputs are Garcia-Molina and Salem (1987) and the current PostgreSQL 18 concurrency-control documentation.
