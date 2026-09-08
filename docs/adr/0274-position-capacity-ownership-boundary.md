# ADR 0274: Separate Position ownership with a fenced capacity protocol

## Status

Proposed — active PR only. This ADR is not protected `develop` truth and does not authorize source extraction until the prerequisite owner stack is normally integrated and the distributed invariant has executable evidence.

## Context

Protected `ARCHITECTURE.md` and `docs/TRD.md` assign Position truth to `organization_core` while `people_core` owns Person, Employment, and Assignment. The executable protected tree does not yet have an `organization_core` service owner; the shipped People mutation boundary still creates Position and serializes Assignment capacity against the Position root. Issue #274 tracks this accepted-architecture versus executable-owner gap.

ADR 0004 already makes `position_record` a durable anchor with bitemporal versions and binds Assignment to Employment, Person, and Position. ADR 0005 already requires Assignment days to be covered by an `active` or `open` Position version and visible allocation for one Position seat to remain at or below `1.0000`. This ADR preserves those semantics. It decides only how Position write/capacity authority can move to `organization_core` without adding cross-service SQL, a second Position writer, or a checked-versus-used race.

PostgreSQL 18 `READ COMMITTED` gives each command a new committed snapshot. A read-only availability check followed by a separate People write therefore does not, by itself, preserve the cross-row seat invariant. PostgreSQL row locks can serialize writers inside one database owner, but service extraction requires an explicit cross-context protocol rather than assuming one local transaction.

A second distributed race exists after a capacity debit is fenced. A point-in-time People read that currently finds no Assignment is not proof that a delayed or in-flight `create_assignment` operation cannot commit later. Releasing capacity from that observation can therefore re-open the seat before the original Assignment commits. Post-fence release needs a terminal People-owned attempt outcome that also fences every later commit for the same attempt.

A third race exists if Position eligibility is treated as a mutable read after the capacity fence. An authentic fence issued while the required Position coverage is `active` or `open` cannot remain safe if Organization may independently commit an overlapping `closed` or otherwise ineligible Position version before People commits Assignment. A People-side recheck does not solve this because Position can change again after the recheck. The Organization reservation therefore has to fence both seat capacity and the Position eligibility required by ADR 0005 for the reservation interval.

Protected assignment validation already accepts a union of visible staffable Position versions when that union covers the whole Assignment interval. A reservation interval may therefore legitimately cross one or more Position-version boundaries while remaining continuously eligible. A single `position_record_version_id` is not sufficient eligibility evidence for that case. The fenced protocol must preserve the canonical visible coverage set, not collapse it into one version identifier.

A separate operability and correctness hazard appears if the Organization transaction tries to solve those races by calling People while holding the Position row lock. PostgreSQL row locks last until transaction end; a remote call under that lock couples database lock lifetime to network/provider latency, enlarges deadlock and pool-exhaustion surfaces, and turns a local aggregate transaction into an implicit distributed lock. Cross-context coordination must therefore occur outside the Position-locking transaction. The local transaction may accept, fence, confirm, release, adjust, or reject from already durable evidence; it may not wait on People while the Position lock is held.

The same evidence rule is required after the initial Assignment is confirmed. A current People read showing a shorter interval, smaller allocation, different Position, ended Assignment, or no row is not sufficient authority to shrink or release an Organization-owned confirmed debit. A delayed correction, retry, conflicting revision, or stale projection could otherwise reopen capacity while the still-authoritative Assignment version remains effective. Every capacity-affecting Assignment mutation therefore needs terminal, immutable People-owned mutation evidence, and any mutation that increases required capacity must fence the positive capacity delta before People can commit it.

Binding a revision command to a prior Assignment version is also insufficient unless People enforces that version as a compare-and-set precondition. Two distinct mutation attempts can otherwise both be prepared against V1, obtain separate valid Organization delta fences, and both commit because locking only their distinct `assignment_attempt_id` values does not serialize the Assignment lineage. Capacity evidence can remain individually authentic while the People history forks. Every revision/end transaction therefore serializes the stable Assignment root and requires its exact expected prior version to remain authoritative at the write linearization point; a stale-predecessor attempt becomes terminally non-committing and its unused delta fences can be released only from that terminal outcome.

Source extraction also needs a real linearization point. Merely rejecting new Assignment commands and then projecting the database is unsafe if a legacy People transaction was admitted before the fence and commits after the projection snapshot. The cutover barrier must reject new legacy admissions and wait until every transaction admitted before the fence has either committed or rolled back before any authoritative migration snapshot is taken.

Transaction drain alone is not enough for a later authority/rollback epoch transition once the cross-context protocol is live. A valid epoch-E `commit_fenced` reservation can exist without an open database transaction or terminal People outcome. If rollback snapshots Assignment history and then supersedes E, that unresolved debit has no lossless legacy projection while a delayed People mutation may still hold authentic E write authority. Stale-epoch rejection after the switch can prevent new mutation, but by itself it can also strand the unresolved debit; if People has not yet adopted the new epoch, a delayed mutation can commit after the rollback snapshot. Retiring an epoch therefore requires a protocol-quiescence barrier in addition to local transaction drain.

Cutover cannot assume the legacy snapshot is valid merely because the legacy writer is authoritative. If the drained snapshot already contains over-allocation, incomplete staffable Position coverage, malformed tenant/identity evidence, or another condition that cannot satisfy ADR 0004/0005 and the new reservation ledger simultaneously, silently dropping, clamping, splitting, rounding, or otherwise normalizing records would create a new truth rather than migrate the old one. Such a discrepancy is a fail-closed cutover finding: authority does not switch until the legacy truth is explicitly corrected under governed ownership and the projection is rerun.

Protected `docs/TRD.md` also preserves retroactive correction as an authoritative bitemporal operation: a correction closes the superseded recorded interval and inserts replacement truth for an earlier effective period. The capacity ledger therefore cannot migrate only assignments whose effective intervals are current or future at cutover. Omitting a wholly past but currently recorded-visible Assignment would make a later retroactive create/correction validate against an incomplete Position occupancy history and could authorize more than `1.0000` on that historical slice. Cutover must project the complete currently authoritative effective-time domain needed by post-cutover retroactive writes; superseded recorded-history versions remain People/audit evidence but do not become duplicate live capacity debits.

## Decision drivers

The design must:

- keep Position and Position capacity as Organization-domain truth while keeping Assignment history as People-domain truth;
- preserve the bitemporal and allocation semantics already Accepted in ADR 0004/0005;
- expose one canonical capacity writer and no cross-service application-table access;
- remain correct under concurrent claims, retries, delayed requests, process loss, message loss/duplication/reordering, ambiguous timeouts, concurrent Position mutation, concurrent Assignment revisions, Assignment correction/end races, and authority/rollback epoch transitions;
- bind idempotency to semantic intent and `assignment_attempt_id`, rather than a caller-controlled key alone;
- authenticate cross-context receipts with issuer, audience, tenant, authority/rollback epoch, exact target version/digest, and replay-safe receipt identity before they become write authority;
- serialize capacity-affecting Assignment revision/end at the stable Assignment root and compare-and-set the exact expected prior Assignment version;
- distinguish terminal People mutation evidence from point-in-time reads or absence observations;
- make a post-fence receipt durable evidence of both consumed capacity and complete Position eligibility coverage for its effective interval;
- require positive capacity/eligibility deltas for Assignment revisions to be fenced before the People revision can commit;
- permit capacity decreases/releases only from immutable terminal People revision/end evidence bound to the exact superseded Assignment and reservation versions;
- keep remote service I/O outside Position-root and Assignment-root transactions and row-lock lifetimes;
- make migration linearizable against legacy in-flight writes and deterministically reproducible from tenant-qualified legacy identities;
- quiesce old-epoch cross-context protocol state before retiring its write authority, so no unresolved fence or unapplied terminal receipt crosses the snapshot boundary silently;
- preserve currently authoritative past-effective occupancy required for retroactive bitemporal correction rather than treating cutover time as an effective-time retention boundary;
- make migration lossless and fail closed when authoritative legacy occupancy cannot satisfy the target invariants without semantic rewriting;
- minimize PII at the Organization boundary; and
- support a fenced cutover from the existing same-database People mutation path without a dual-writer interval.

## Alternatives

### A. Move Position and Assignment into one Organization aggregate/service

This gives the simplest local transaction for seat allocation, but it moves worker Assignment history out of the protected `people_core` ownership model and couples employment-lifecycle truth to structural Organization ownership. Reject for now.

### B. Keep Position in Organization and call a synchronous availability read before People writes Assignment

This preserves nominal ownership but is not sufficient for correctness. Between availability read and Assignment commit, another writer can consume the same capacity or change Position eligibility. Reject as a TOCTOU design.

### C. Organization-owned `PositionCapacityReservation` with commit fences and People-owned terminal mutation outcomes

Provisionally selected. `organization_core` is the sole writer for Position status/version and Position capacity. `people_core` remains the sole writer for Assignment history and for terminal outcomes of capacity-affecting Assignment mutation attempts. Their shared invariant is represented by a versioned protocol rather than cross-service SQL.

### D. Two-phase Assignment visibility

People first stores an Assignment in a non-active `pending_capacity` state, Organization confirms capacity, and People then activates it. This avoids a non-expiring unresolved capacity debit but adds another authoritative Assignment lifecycle state plus activation/reconciliation failure windows. Keep as the principal alternative until option C has executable failure evidence; do not mark this ADR Accepted merely because option C is currently preferred.

## Domain model and ubiquitous language

`organization_core` owns:

- `Position`: aggregate root for one tenant-qualified staffable seat and its bitemporal status/version evidence.
- `PositionCapacityReservation`: entity under Position capacity authority. It binds an opaque reservation identifier, tenant, Position, allocation ratio, effective interval, opaque `assignment_attempt_id`, assignment mutation intent/reference, canonical Position eligibility coverage evidence, idempotency key, semantic command digest that includes the exact `assignment_attempt_id`, lifecycle state, predecessor/supersession evidence where applicable, owner authority/rollback epoch, and immutable audit/outbox correlation.
- `PositionEligibilityCoverage`: value object containing the canonical ordered set of visible Position-version interval slices whose union covers the reservation interval at the fence's knowledge cutoff. Each element carries the exact `position_record_version_id` and intersecting valid-time slice; the normalized set and cutoff are digest-bound.
- `AllocationRatio` and `EffectiveInterval`: value objects used to calculate overlapping capacity.

`people_core` owns:

- `Assignment`: aggregate-root history fact bound to tenant, Employment, Person, Position, allocation, effective interval, and the exact Organization capacity/eligibility evidence that authorized the effective write. Capacity-affecting revisions serialize this stable Assignment root and compare-and-set the exact expected prior version before a new authoritative version/end can commit.
- `AssignmentAttemptOutcome`: terminal, tenant-qualified protocol evidence for one opaque `assignment_attempt_id`. Each capacity-affecting create, revise, move, shorten, or end attempt gets its own attempt identity. The semantic digest binds operation kind, the exact `assignment_attempt_id`, exact stable Assignment identity and expected prior version when one exists, exact prior Organization reservation version/digest set, requested resulting Assignment facts, and each new Organization delta-fence receipt with its target reservation identity/version/digest. The terminal outcome records every referenced fence disposition as `consumed` or `unused_releasable`; Organization must compare-and-set the expected reservation version before confirming or releasing that fence. Its terminal state is `committed` with the authoritative resulting Assignment version/end receipt or `aborted` with an immutable abort/conflict tombstone. A terminal `aborted` outcome fences every later retry for that same attempt from committing.

No Person name, compensation, rating, assessment result, or other worker payload is copied into `PositionCapacityReservation`. The cross-context protocol carries only opaque references, semantic digests, normalized eligibility coverage evidence, and terminal receipts required to enforce the seat invariant.

## Capacity and Position-eligibility invariants

While a reservation debit is effective, `held`, `commit_fenced`, and `confirmed` states consume capacity. `released`, `expired`, and `cancelled` states do not. Only `held` may expire autonomously.

For every tenant-qualified Position and every overlapping valid-time slice:

`sum(allocation_ratio for effective held + commit_fenced + confirmed reservation debits) <= 1.0000`

Every effective `commit_fenced` or `confirmed` debit also requires Organization-owned Position state to remain assignment-eligible (`active` or `open` under ADR 0005) for its interval. Its `PositionEligibilityCoverage` must cover that entire interval as a normalized union; a Position mutation that would invalidate any covered slice while such a debit exists cannot commit as an unrelated independent change.

For an Assignment revision, Organization computes capacity by effective Position/time slice. Existing confirmed debits remain authoritative until immutable People evidence allows their reduction or release. Any positive delta between the proposed resulting Assignment occupancy and already confirmed occupancy must be represented by one or more new `held -> commit_fenced` debits before People may commit that revision. Decreases need no speculative release before People commit; temporary over-reservation is safe, while temporary under-reservation is not.

`organization_core` enforces these rules by serializing reservation and Position-status/version mutations at the stable Position root and re-reading authoritative overlapping debit and Position-version sets inside that local transaction. `people_core` independently serializes each existing Assignment lineage at its stable Assignment root and rejects a revision whose expected prior version is no longer authoritative. A stale read model is never capacity, eligibility, or Assignment-lineage authority, and neither owner performs cross-context I/O while holding its local root lock.

## Protocol

1. `reserve`: under Position-root serialization, validate Position status/version coverage and capacity, then create `held`. The idempotency record is tenant-qualified and stores the idempotency key, exact `assignment_attempt_id`, semantic command digest, resulting reservation identity/version, and issuing authority/rollback epoch. The semantic digest itself includes the exact `assignment_attempt_id`. Exact replay of the same key, attempt ID, digest, and epoch returns the same reservation; the same key with a different attempt ID, digest, or authority context fails closed.
2. `arm_commit_fence`: under the same Position-root authority, compare-and-set the exact expected reservation version and verify that the stored `assignment_attempt_id`, semantic digest, and authority epoch still match the command. Revalidate capacity and complete `active`/`open` coverage for the exact effective interval, normalize `PositionEligibilityCoverage`, and convert `held` to `commit_fenced`. This is durable, idempotent for the same reservation version/attempt/digest, coverage-digest-bound, non-expiring, and becomes an Organization promise not to commit an incompatible Position-status/version transition while the debit remains `commit_fenced` or `confirmed`. A mismatched attempt ID, digest, expected version, or retired epoch fails closed.
3. `create_assignment`: after the Organization transaction has completed, People accepts only a verified cross-context Organization receipt proving the exact reservation is `commit_fenced` for the same tenant, Position, allocation, effective interval, semantic intent, complete Position eligibility coverage digest, `assignment_attempt_id`, reservation version/digest, and currently admitted authority epoch. Receipt verification follows the authenticated-envelope contract below before the receipt can authorize a People write. Inside one People transaction, it serializes the attempt identity and either writes Assignment plus terminal `AssignmentAttemptOutcome=committed` atomically, returns the existing equivalent terminal outcome, or fails closed on contradictory evidence. A terminal `aborted` attempt can never later commit.
4. `terminalize_attempt`: reconciliation may ask People to resolve an exact unresolved attempt. People serializes on `assignment_attempt_id`; if that attempt already committed, it returns the terminal `committed` outcome. Otherwise it writes a durable terminal `aborted` tombstone that prevents every delayed or retried mutation for that attempt from committing. A point-in-time `not found`, empty result, HTTP timeout, or missing event is not a terminal outcome.
5. `confirm`: in a new Organization transaction, Organization converts `commit_fenced` to `confirmed` only from an already-obtained and authenticated terminal People `committed` receipt for the exact attempt/reservation/version/digest. The receipt's fence disposition must mark that target as `consumed`, and Organization compare-and-sets the exact expected reservation version. Duplicate or reordered equivalent confirmation is idempotent; stale version, contradictory disposition, different digest, or retired authority context fails closed. The Organization transaction does not call People while holding the Position lock.
6. `revise_assignment_capacity`: each capacity-affecting correction, move, interval change, allocation change, or end is a new People mutation attempt bound to the stable Assignment identity, exact expected prior Assignment version, and exact prior reservation evidence. Before People can commit an increase, interval extension, or Position move, Organization reserves and arms all positive target capacity/eligibility deltas. For a same-Position increase this may be only the additional allocation/time slices; for a Position move it is the full target occupancy not already backed on the target Position. People then starts one local transaction, serializes both the mutation attempt and stable Assignment root, verifies the expected prior version is still authoritative, and only then atomically writes the new Assignment version/end plus terminal `committed` outcome. If another mutation already advanced the Assignment lineage, this attempt cannot commit from the stale predecessor; it records/returns terminal non-committing `aborted` conflict evidence for this attempt so any unused delta fences can be released idempotently. The caller must start a new attempt against current authoritative evidence rather than replaying the stale command under a new key.
7. `apply_revision_receipt`: after People commits a revision/end, Organization applies the already-obtained authenticated terminal receipt in one or more new Position-local transactions. Each fence transition is bound to the receipt's exact target reservation identity/version/digest and `consumed` or `unused_releasable` disposition, and Organization compare-and-sets that expected reservation version. New delta fences are confirmed before superseded debits are reduced/released. Across a Position move, target capacity is therefore confirmed before source capacity is released. Same-Position incremental debits may remain as multiple confirmed ledger entries whose effective sum equals the new Assignment occupancy; later compaction, if implemented, must be evidence-preserving and cannot change effective capacity. A confirmed debit is never shrunk or released from a mutable People read, current absence, timeout, event-delivery state, elapsed time, or a receipt from a retired epoch.
8. `release_uncommitted`: an ordinary `held` reservation may be released or expire before a commit fence. A `commit_fenced` debit for an unresolved or stale-predecessor-aborted attempt may return capacity only from an already-obtained authenticated terminal People `aborted` receipt for the exact attempt and target reservation identity/version/digest whose disposition is `unused_releasable`. Applying the durable receipt compare-and-sets that reservation version in a local Organization transaction; obtaining and authenticating it happens outside the Position lock.
9. `change_position_status_or_version`: Organization serializes the proposed mutation at the same Position root. If the change would remove eligible coverage from any slice consumed by `commit_fenced` or `confirmed` debits, this transaction fails closed with durable conflict/audit evidence and ends without making a People call. A separate governed workflow may then terminalize or correct affected People attempts/Assignments outside any Position lock, apply resulting terminal receipts in new local Organization transactions, and retry the exact status/version command against the new Position/reservation version.

### Authenticated cross-context receipt envelope

Capacity and terminal-outcome receipts are durable write authority, so transport authentication alone is insufficient once a receipt is persisted, queued, or replayed. Both directions use a versioned canonical envelope whose signed fields include `contract_version`, globally unique `receipt_id`, `issuer_context`, `audience_context`, tenant, monotonic owner `authority_epoch`, monotonic `rollback_epoch`, exact `assignment_attempt_id`, semantic command digest, issued receipt version, and canonical payload digest. Organization capacity payloads additionally bind Position, effective interval, allocation, reservation identity/version/state, and `PositionEligibilityCoverage` digest. People terminal payloads bind stable Assignment identity, expected prior/resulting Assignment version, exact prior and target reservation identity/version/digest set, and each fence disposition.

The canonical owner signs the canonical envelope with an owner-controlled asymmetric signing key identified by immutable `key_id`/key version; the consumer verifies the signature against the released, versioned verification-key set bound to the expected owner identity before any domain transition. Keyverse-backed service identity and mutually authenticated transport may authenticate the live channel, but neither substitutes for receipt integrity after transport. A receipt whose signature, issuer, audience, tenant, owner epoch, rollback epoch, contract version, target reservation/Assignment version or digest does not match the consumer's pinned authority state fails closed.

Replay protection is idempotency-preserving rather than timeout-based: byte-equivalent replay of the same `receipt_id` and canonical payload may return the same result while that authority epoch remains admitted or after the same terminal result is already durably recorded; reuse of that `receipt_id` with a different canonical payload, attempt ID, target, version, digest, issuer/audience, tenant, or authority epoch is contradictory evidence and fails closed. A retired authority/rollback epoch cannot authorize a new domain transition even when the signature is otherwise valid. Historical receipts and keys remain verifiable as audit/reconciliation evidence, but verification alone does not restore retired write authority.

A timeout may enqueue reconciliation; it may not undo a commit fence, shrink a confirmed debit, infer a terminal People state, or advance an authority epoch. No remote timeout extends a Position or Assignment database lock because cross-context calls are never made from either root-locking transaction.

## Failure and recovery semantics

- Crash after `held` but before commit fence: bounded expiry may reclaim capacity.
- Crash after commit fence before People receives or commits the mutation: capacity and Position eligibility stay fenced. Reconciliation may terminalize the attempt, but release occurs only after People durably records `aborted` and thereby fences all future commits for that attempt.
- Delayed/in-flight mutation racing `terminalize_attempt`: People serializes both by `assignment_attempt_id`, so exactly one terminal outcome wins.
- Two distinct revisions prepared from the same prior Assignment version: each may have authentic delta fences, but People serializes the stable Assignment root and compare-and-sets the expected predecessor. At most one can advance that lineage from the same version. The loser becomes terminally non-committing and its unused delta fences remain reserved until Organization receives the exact authenticated abort/conflict receipt with matching reservation versions and `unused_releasable` dispositions.
- Crash after People commits Assignment plus terminal `committed` outcome but before Organization receives `confirm`: capacity and Position eligibility stay fenced; a second overlapping claim that would exceed `1.0000` is rejected. Reconciliation confirms from authoritative People evidence.
- Allocation increase or interval extension: the positive delta is fenced before People commit. A crash after People commit but before delta confirmation leaves both old confirmed occupancy and the new delta commit-fenced, so capacity remains conservative rather than under-reserved.
- Allocation decrease, shortening, or end: People may commit first, but the old confirmed debit remains until the terminal revision receipt is applied. A crash in that window causes temporary under-utilization, not overbooking.
- Position move: target capacity/eligibility is commit-fenced before People commit; after People commit, Organization confirms target evidence before releasing source evidence. Crashes or reordered delivery can temporarily reserve both Positions but cannot leave the moved Assignment without target capacity/eligibility.
- Stale or duplicated revision receipt: the receipt is authenticated and bound to exact prior Assignment and reservation versions/digests plus fence dispositions. It either replays idempotently or fails closed; it cannot release a debit superseded by a different authoritative revision.
- Forged, wrong-audience, cross-tenant, stale-epoch, rollback-epoch, replay-with-different-payload, or mismatched-target receipt: reject before the receipt can authorize a People or Organization transition; record fail-closed security/audit evidence.
- Position status/version mutation racing a fenced Assignment attempt: the local Organization mutation serializes against the same Position root and live debit set. If the proposed change would make an effective slice ineligible, it exits with conflict rather than calling People under the lock.
- Crash during external Position-change coordination: the original Position eligibility coverage/fence remains authoritative because the rejected Organization transaction made no eligibility change. Idempotent People terminalization/correction and Organization receipt application can resume without a distributed lock.
- Lost, duplicated, or reordered confirm/release/revision messages: authenticated attempt/reservation version, semantic digest, fence disposition, receipt identity, and authority epoch preserve one result or fail closed on contradiction.
- Epoch retirement with unresolved protocol state: the authority switch stays blocked. Old-epoch state is settled under a protocol-quiescence barrier before the epoch is superseded; stale-epoch rejection is not used as a substitute for settlement.
- Reconciliation records evidence and decisions in immutable audit/outbox data. It cannot infer terminal absence from time, request delivery state, or a current read that finds no Assignment.

This is a Saga-style compensating protocol, not a distributed ACID claim. Compensations are explicit domain transitions with evidence; retries, TTLs, present-time absence, transport observations, and a network call made while holding a database row lock are not substitutes for atomicity or terminal-outcome evidence.

## Cutover, protocol quiescence, and rollback

Extraction must not create two Position/capacity writers. A migration snapshot must be linearized after every legacy write admitted before the fence. A later rollback or protocol-authority transition must additionally prove that no nonterminal cross-context state from the retiring epoch can mutate truth after the snapshot.

### Initial legacy-to-Organization cutover

1. Integrate #64 normally so the currently shipped People mutation/concurrency truth is protected.
2. Integrate #96 and then #119 through their canonical Organization stack; descendants adopt protected predecessors with ordinary non-force history.
3. Implement and test the Organization owner and published/versioned capacity contract while this ADR remains Proposed.
4. Enter a durable cutover epoch that rejects new legacy Position/Assignment capacity-mutation admissions. Every mutation admitted before the epoch change must hold a transaction-lifetime admission receipt tied to the same cutover barrier; the barrier cannot close until each such receipt has terminally committed or rolled back. A sleep, request-counter sample, one `pg_stat_activity` observation, or elapsed-time assumption is not drain evidence.
5. Only after that barrier closes, record the authoritative cutover knowledge timestamp/high-water evidence and take the migration snapshot. Project every Assignment fact that is currently recorded-visible at that cutoff across the complete effective-time domain, including wholly past intervals that remain subject to retroactive correction, into the Organization reservation ledger and bind the projection to an immutable manifest/digest. Superseded recorded-history versions remain People/audit provenance and must not be duplicated as simultaneously live reservation debits.
6. The manifest must define a deterministic, versioned mapping from each tenant-qualified legacy `assignment_record_id` in that complete currently authoritative effective-time projection to one opaque migration `assignment_attempt_id`, one reservation identity, and terminal People `committed` evidence rooted in the already-authoritative Assignment. The mapping algorithm/version, exact Assignment effective/recorded evidence, allocation, Position, and normalized `PositionEligibilityCoverage` are manifest inputs; replay of the same snapshot must produce byte-identical identifiers/digests. Existing committed Assignments project as `confirmed`, never as expirable `held` or unresolved `commit_fenced`.
7. Before authority switch, verify tenant, Position, effective interval, allocation, eligibility-coverage union, aggregate sum, deterministic identifier/digest, and terminal-outcome equivalence for the complete projection across past, present, and future effective slices. Any source Assignment that cannot be represented losslessly, any aggregate allocation above `1.0000`, any incomplete staffable Position coverage, or any ambiguous tenant/identity mapping aborts the authority switch. Emit immutable discrepancy evidence; do not drop, clamp, split, round, synthesize, or silently rewrite the legacy fact to make the target ledger pass.
8. Switch Position/capacity write authority to `organization_core`, then switch `people_core` to the published capacity/attempt protocol, then remove the cutover fence. The authority switch establishes the signed owner authority/rollback epoch pair used by the cross-context receipt contract. No legacy transaction admitted before the fence remains able to commit after the projection or authority switch.

### Retiring a live protocol epoch

Rollback, contract-owner migration, or any other change that makes epoch E stale follows a two-sided protocol-quiescence sequence before E is superseded:

1. Organization enters `draining(E)` and rejects creation of new E `held` reservations and new E commit fences. Existing capacity remains authoritative.
2. People then enters `draining(E)` for new mutations authorized by E receipts. Every People mutation already admitted under E holds a transaction-lifetime protocol-admission receipt; the barrier waits for those admitted transactions to commit or roll back. Delayed requests that were never admitted cannot enter after this barrier.
3. After the People admission drain closes, reconcile every E `held` and `commit_fenced` reservation. A safe `held` may expire or release according to its ordinary rules. Every `commit_fenced` attempt must reach a terminal People `committed` or `aborted` outcome now that no new E create/revision can be admitted; apply that exact terminal receipt to Organization so no E `commit_fenced` debit remains unresolved.
4. Apply every terminal E revision/end/confirm/release receipt required to make Organization confirmed capacity state and People authoritative Assignment history equivalent. Drain those Organization local transactions. The quiescence manifest records all retiring-epoch attempts/reservations, terminal outcome IDs/digests, applied reservation versions/dispositions, and proves zero unresolved `commit_fenced` state and zero unapplied capacity-changing terminal outcomes.
5. Only after protocol quiescence is proven may the rollback/migration high-water snapshot be taken. `confirmed` occupancy can be projected because it is bound to terminal Assignment evidence. The target writer projection must be equivalent across the complete effective-time domain required for retroactive correction.
6. Increment the rollback/authority epoch and activate exactly one target writer. New domain transitions reject E receipts. Historical E receipts remain auditable but cannot regain write authority.

A design that intentionally carries unresolved protocol state across an epoch instead of quiescing it must define a versioned successor-epoch re-attestation/handoff manifest that binds each exact reservation, attempt, terminal/nonterminal state, target version/digest, and one successor authority decision without permitting both epochs to authorize writes. This ADR does not select that more complex alternative.

Rollback must be rehearsed before un-fencing. It uses both the local transaction barrier and the protocol-quiescence barrier above, proves projection equivalence at its rollback cutoff, increments the rollback/authority epoch only after the retiring epoch is quiescent, and never re-enables both the legacy People Position/capacity writer and the Organization writer.

## Acceptance before Accepted status

This ADR may move from Proposed only after the owner stack has executable evidence for all of the following on the exact candidate head:

- two concurrent `0.6000` reservations for one Position and overlapping interval: exactly one succeeds;
- non-overlapping future intervals can both succeed when their own slices remain within capacity;
- exact replay versus same-key/different-digest behavior, plus same-key/different-`assignment_attempt_id` rejection;
- forged signature, wrong issuer/audience, cross-tenant receipt, stale owner epoch, stale rollback epoch, same-`receipt_id`/different-payload replay, and mismatched reservation/Assignment target version or digest all fail closed before a cross-context receipt can authorize a write;
- byte-equivalent authenticated receipt replay is idempotent and does not use wall-clock expiry as write authority;
- crash after `held` before commit fence and bounded expiry;
- crash after commit fence before People commit with no release from mere absence;
- a deliberately delayed `create_assignment` racing attempt terminalization: exactly one terminal People outcome (`committed` or `aborted`) wins;
- two distinct correction attempts based on the same prior Assignment version: at most one advances the Assignment root, the stale-predecessor loser is terminally non-committing, and its unused delta fences remain reserved until exact authenticated abort/conflict evidence with target reservation version/digest and `unused_releasable` disposition is applied;
- a Position close/status-version change racing a fenced create: Organization cannot make the reservation interval ineligible while People can still commit from the authentic fence receipt;
- a reservation spanning multiple contiguous staffable Position versions: canonical eligibility coverage must span the whole interval and an incompatible change to any covered slice must fail closed;
- instrumentation proving Position-root and Assignment-root database transactions perform no cross-context network I/O and remote latency cannot extend either root-lock lifetime;
- crash after Assignment commit before confirm with capacity and eligibility remaining fenced;
- a same-Position allocation increase where only the positive delta is pre-fenced and no interleaving exposes allocation above `1.0000`;
- an interval extension where newly occupied slices are pre-fenced before People revision commit;
- a Position move where target occupancy is fenced before People commit and source capacity is not released until target confirmation/revision evidence is durable;
- allocation decrease, interval shortening, and Assignment end where stale/current reads cannot release confirmed capacity and a crash after People commit causes only temporary over-reservation;
- delayed, duplicated, stale, and out-of-order revision receipts bound to exact prior Assignment/reservation versions and fence dispositions, with contradictory evidence failing closed;
- lost/duplicated/out-of-order confirm/release messages with authenticated version/digest-bound idempotency;
- a pre-fence legacy Assignment transaction deliberately held open while cutover starts: projection cannot begin until that transaction commits or rolls back;
- deterministic legacy projection replay with identical migration identities, terminal committed evidence, eligibility-coverage digests, and manifest digest across every currently authoritative past/present/future effective slice;
- a post-cutover retroactive correction or create against a wholly past interval is checked against migrated historical occupancy and cannot make that Position slice exceed `1.0000` or bypass staffable Position coverage;
- deliberately invalid legacy occupancy causing deterministic discrepancy evidence, no authority switch, and no silent normalization;
- an epoch-E `commit_fenced` attempt deliberately left without terminal People outcome while rollback starts: rollback cannot take its authoritative snapshot or supersede E until People E admission is fenced/drained, exactly one terminal outcome is established, and its capacity disposition is applied;
- a delayed epoch-E create racing protocol quiescence cannot commit after the People E admission barrier closes; if it was admitted before the barrier, rollback waits for its transaction and terminal outcome before the snapshot;
- protocol-quiescence manifest replay proves zero unresolved E `commit_fenced` debits, zero unapplied capacity-changing E terminal outcomes, and equivalence between confirmed Organization occupancy and authoritative People Assignment truth before epoch rollover;
- after E is superseded, an otherwise valid E receipt cannot authorize a new domain transition and no E debit/attempt remains orphaned;
- migration projection equivalence and rollback rehearsal without a dual-writer interval;
- real two-service/PostgreSQL interleavings proving no effective slice exposes allocation above `1.0000`, no Assignment write is authorized outside fenced Position eligibility, and no cross-service SQL exists;
- connection/resource cleanup and immutable audit/outbox evidence for failures as well as success; and
- buyer-path reserve/fence/create/terminalize/confirm/revise/apply-revision/release plus conflicting Position-change measurements at p95 <= 20 ms under real concurrency without sample shrinking, excluded slow paths, or warm-cache-only evidence.

Synthetic fixtures may prove deterministic mechanism behavior. Buyer-realistic or scientific claims require provenance-backed right-cleared data.

## Consequences

- Position ownership can match the accepted context map without moving worker Assignment history into Organization.
- Capacity and Position eligibility become explicit Organization domain authority rather than implicit People SQL reads.
- Eligibility evidence is a normalized coverage set; no arbitrary single-version shortcut is allowed.
- A post-fence debit cannot be released merely because People currently shows no Assignment; release requires terminal People evidence that also fences a delayed commit for that attempt.
- Confirmed capacity is also evidence-bound after Assignment correction/end. A mutable current read cannot shrink or release it.
- Concurrent revisions cannot fork one Assignment lineage merely because they use distinct attempt IDs: the stable Assignment root and expected-prior-version CAS form the People-side linearization point.
- Capacity-increasing revisions reserve only their positive Position/time-slice delta before People commit; capacity-decreasing revisions release only after terminal People commit evidence. Failures therefore prefer temporary over-reservation to under-reservation or overbooking.
- Cross-Position moves fence and then confirm target capacity before source release, so recovery never depends on a distributed row lock or a check-then-write read.
- Organization cannot independently close or invalidate a fenced effective slice while People can still commit from the authentic receipt.
- Cross-context coordination is deliberately not performed under the Position or Assignment root lock.
- Cross-context write-authority receipts survive queues/retries with cryptographic source/integrity proof, explicit issuer/audience/tenant and authority epochs; equivalent replay stays idempotent while forged, retired-epoch, or contradictory replay fails closed.
- Initial cutover has an explicit transaction-drain linearization point and a deterministic legacy Assignment-to-confirmed-reservation mapping across the complete currently authoritative effective-time domain, including past slices required for retroactive correction.
- Retiring a live protocol epoch also requires two-sided protocol admission drain and settlement of every unresolved fence/capacity-changing terminal outcome before the snapshot and epoch rollover.
- Invalid or unrepresentable legacy occupancy is surfaced as immutable migration discrepancy evidence and blocks authority switch.
- Ambiguous post-fence failures fail closed as capacity/eligibility reservation until explicit terminal People evidence exists.
- The protocol adds reservation state, People attempt-outcome fencing, authenticated revision receipts, Assignment-root CAS, Position eligibility fencing, protocol-quiescence barriers, reconciliation, and operational evidence that a single local transaction does not require; that cost is accepted only if executable evidence confirms the bounded-context separation remains worthwhile.
- ADR 0004/0005 remain Accepted semantic authority. This ADR amends only the future service-ownership/consistency mechanism after successful extraction evidence.

## References

See `docs/doctoring/position-capacity-reservation-references.md` for APA 7th records and design mapping. The primary design inputs are Garcia-Molina and Salem (1987) and the current PostgreSQL 18 concurrency-control documentation.