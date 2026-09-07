# ADR 0274: Separate Position ownership with a fenced capacity protocol

## Status

Proposed — active PR only. This ADR is not protected `develop` truth and does not authorize source extraction until the prerequisite owner stack is normally integrated and the distributed invariant has executable evidence.

## Context

Protected `ARCHITECTURE.md` and `docs/TRD.md` assign Position truth to `organization_core` while `people_core` owns Person, Employment, and Assignment. The executable protected tree does not yet have an `organization_core` service owner; the shipped People mutation boundary still creates Position and serializes Assignment capacity against the Position root. Issue #274 tracks this accepted-architecture versus executable-owner gap.

ADR 0004 already makes `position_record` a durable anchor with bitemporal versions and binds Assignment to Employment, Person, and Position. ADR 0005 already requires Assignment days to be covered by an `active` or `open` Position version and visible allocation for one Position seat to remain at or below `1.0000`. This ADR preserves those semantics. It decides only how Position write/capacity authority can move to `organization_core` without adding cross-service SQL, a second Position writer, or a checked-versus-used race.

PostgreSQL 18 `READ COMMITTED` gives each command a new committed snapshot. A read-only availability check followed by a separate People write therefore does not, by itself, preserve the cross-row seat invariant. PostgreSQL row locks can serialize writers inside one database owner, but service extraction requires an explicit cross-context protocol rather than assuming one local transaction.

## Decision drivers

The design must:

- keep Position and Position capacity as Organization-domain truth while keeping Assignment history as People-domain truth;
- preserve the bitemporal and allocation semantics already Accepted in ADR 0004/0005;
- expose one canonical capacity writer and no cross-service application-table access;
- remain correct under concurrent claims, retries, process loss, message loss/duplication/reordering, and ambiguous timeouts;
- bind idempotency to semantic intent rather than a caller-controlled key alone;
- minimize PII at the Organization boundary; and
- support a fenced cutover from the existing same-database People mutation path without a dual-writer interval.

## Alternatives

### A. Move Position and Assignment into one Organization aggregate/service

This gives the simplest local transaction for seat allocation, but it moves worker Assignment history out of the protected `people_core` ownership model and couples employment-lifecycle truth to structural Organization ownership. Reject for now.

### B. Keep Position in Organization and call a synchronous availability read before People writes Assignment

This preserves nominal ownership but is not sufficient for correctness. Between availability read and Assignment commit, another writer can consume the same capacity. Reject as a TOCTOU design.

### C. Organization-owned `PositionCapacityReservation` with a commit fence

Provisionally selected. `organization_core` is the sole writer for Position status/version and Position capacity. `people_core` remains the sole writer for Assignment history. Their shared invariant is represented by a versioned protocol rather than cross-service SQL.

### D. Two-phase Assignment visibility

People first stores an Assignment in a non-active `pending_capacity` state, Organization confirms capacity, and People then activates it. This avoids a non-expiring unresolved capacity debit but adds another authoritative Assignment lifecycle state plus activation/reconciliation failure windows. Keep as the principal alternative until option C has executable failure evidence; do not mark this ADR Accepted merely because option C is currently preferred.

## Domain model and ubiquitous language

`organization_core` owns:

- `Position`: aggregate root for one tenant-qualified staffable seat and its bitemporal status/version evidence.
- `PositionCapacityReservation`: entity under the Position capacity authority. It binds an opaque reservation identifier, tenant, Position, allocation ratio, effective interval, assignment intent/reference, exact Position version/evidence, idempotency key, semantic command digest, lifecycle state, and immutable audit/outbox correlation.
- `AllocationRatio` and `EffectiveInterval`: value objects used to calculate overlapping capacity.

`people_core` owns:

- `Assignment`: employment-history fact bound to tenant, Employment, Person, Position, allocation, effective interval, and the exact Organization capacity receipt that authorized the write.

No Person name, compensation, rating, assessment result, or other worker payload is copied into `PositionCapacityReservation`. The protocol carries only the references and evidence required to enforce the seat invariant.

## Capacity invariant

While a reservation is effective, `held`, `commit_fenced`, and `confirmed` states consume capacity. `released`, `expired`, and `cancelled` states do not. Only `held` may expire autonomously.

For every tenant-qualified Position and every overlapping valid-time slice:

`sum(allocation_ratio for effective held + commit_fenced + confirmed reservations) <= 1.0000`

`organization_core` enforces this by serializing capacity mutations at the stable Position root and re-reading the authoritative overlapping capacity debit set inside that transaction. A stale read model is never capacity authority.

## Protocol

1. `reserve`: under Position-root serialization, validate Position status/version and capacity, then create `held`. Exact replay of the same idempotency key and semantic digest returns the same reservation; the same key with a different digest fails closed.
2. `arm_commit_fence`: convert the exact `held` reservation to `commit_fenced`. This is durable, idempotent, version-bound, and non-expiring.
3. `create_assignment`: People may commit Assignment only from an authentic receipt issued through the released/versioned Organization contract proving the exact reservation is `commit_fenced` for the same tenant, Position, allocation, effective interval, and semantic intent.
4. `confirm`: after People has an authoritative committed Assignment receipt, Organization converts the debit to `confirmed` and binds that receipt. Duplicate or reordered confirmation is idempotent when version/digest-equivalent and fails closed when contradictory.
5. `release`/`adjust`: an ordinary `held` reservation may be released or expire before a commit fence. A `commit_fenced` debit may return capacity only after authoritative People evidence proves Assignment abort/absence or a later governed correction/end makes the debit no longer effective. Timeout, elapsed time, one missing event, one HTTP failure, or a stale read is never proof of absence.

A timeout may enqueue reconciliation; it may not undo a commit fence.

## Failure and recovery semantics

- Crash after `held` but before commit fence: bounded expiry may reclaim capacity.
- Crash after commit fence but before People commit: capacity stays consumed until an authoritative People abort/absence outcome resolves it.
- Crash after People commit but before `confirm`: capacity stays consumed; a second overlapping claim that would exceed `1.0000` is rejected. Reconciliation confirms from authoritative People evidence.
- Lost, duplicated, or reordered confirm/release messages: version/digest-bound idempotency preserves one outcome or fails closed on contradiction.
- Position version/status changes while a reservation is in flight: the transition policy must revalidate the exact version/evidence required by the command. A stale receipt cannot silently authorize a new Assignment.
- Reconciliation records its evidence and decision in immutable audit/outbox data. It cannot infer non-existence from time alone.

This is a Saga-style compensating protocol, not a distributed ACID claim. Compensations are explicit domain transitions with evidence; retries and TTLs are transport/recovery mechanisms, not atomicity.

## Cutover and rollback

Extraction must not create two Position/capacity writers.

1. Integrate #64 normally so the currently shipped People mutation/concurrency truth is protected.
2. Integrate #96 and then #119 through their canonical Organization stack; descendants adopt protected predecessors with ordinary non-force history.
3. Implement and test the Organization owner and released/versioned capacity contract while this ADR remains Proposed.
4. Before authority switch, fence new Assignment capacity mutations.
5. Project current and future-effective Assignment occupancy into the Organization reservation ledger. Bind the projection to an immutable migration manifest/digest and verify tenant, Position, effective interval, allocation, and aggregate-sum equivalence.
6. Switch Position/capacity write authority to `organization_core`, then switch `people_core` to the released capacity contract, then remove the fence.

Rollback must be defined and rehearsed before un-fencing. It must select one writer authority; it must never re-enable both the legacy People Position/capacity writer and the Organization writer.

## Acceptance before Accepted status

This ADR may move from Proposed only after the owner stack has executable evidence for all of the following on the exact candidate head:

- two concurrent `0.6000` reservations for one Position and overlapping interval: exactly one succeeds;
- non-overlapping future intervals can both succeed when their own slices remain within capacity;
- exact replay versus same-key/different-digest behavior;
- all failure windows above, including commit-fenced ambiguity and authoritative reconciliation;
- stale Position version/status rejection;
- Assignment correction/end and capacity adjustment without leakage or overbooking;
- migration projection equivalence and rollback rehearsal without a dual-writer interval;
- real two-service/PostgreSQL interleavings proving no effective slice exposes allocation above `1.0000` and proving no cross-service SQL;
- connection/resource cleanup and immutable audit/outbox evidence for failures as well as success; and
- buyer-path reserve/fence/confirm/release measurements at p95 <= 20 ms under real concurrency without sample shrinking, excluded slow paths, or warm-cache-only evidence.

Synthetic fixtures may prove deterministic mechanism behavior. Buyer-realistic or scientific claims require provenance-backed right-cleared data.

## Consequences

- Position ownership can match the accepted context map without moving worker Assignment history into Organization.
- Capacity becomes an explicit Organization domain authority rather than an implicit People SQL read.
- Ambiguous post-fence failures fail closed as bounded capacity leakage until authoritative reconciliation, preferring temporary under-utilization over durable overbooking.
- The protocol adds state, reconciliation, and operational evidence that a single local transaction does not require; that cost is accepted only if executable evidence confirms the bounded-context separation remains worthwhile.
- ADR 0004/0005 remain Accepted semantic authority. This ADR amends only the future service-ownership/consistency mechanism after successful extraction evidence.

## References

See `docs/doctoring/position-capacity-reservation-references.md` for APA 7th records and design mapping. The primary design inputs are Garcia-Molina and Salem (1987) and the current PostgreSQL 18 concurrency-control documentation.