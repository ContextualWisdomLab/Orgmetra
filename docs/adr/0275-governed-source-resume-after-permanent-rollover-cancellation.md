# ADR 0275: Govern source resume after permanent rollover cancellation

## Status

Proposed — active PR only. This decision extends the recovery state machine proposed in ADR 0274. It does not make ADR 0274 Accepted, does not authorize Position source extraction, and does not supersede the prerequisite integration order recorded there.

## Problem

ADR 0274 deliberately keeps the source `(authority_epoch=E, rollback_epoch=R)` business-admission gates closed after a retryable `aborted` transition. That is required so a retry can reuse the same immutable source-boundary closure receipts and high-water marks without source-pair ABA.

The same rule becomes a liveness failure when governance permanently abandons the target rollout before activation. The source writer is still authoritative, but both owners can remain unable to admit HR mutations indefinitely. Reopening the old `(E,R)` gates is not safe: work admitted after the original closure high-water would share an authority pair with evidence that already claims the pair was closed and drained.

Permanent cancellation therefore needs a distinct terminal recovery path. It is an authority-boundary transition, not a retry and not a rollback of HR domain facts.

A second race exists if owner-local adoption of `(E,R+1)` is allowed while the durable rollover lineage is still `aborted`. A retry controller can win `aborted -> draining` after one owner has already installed the fresh source pair, leaving the control plane split between retry and resume. Permanent cancellation therefore needs a transition-level linearization point before either owner mutates its local authority state.

## Decision

A retryable `aborted` transition continues to reserve its exact source pair and may only retry the byte-equivalent original target intent under ADR 0274. Permanent abandonment uses a separate `source_resume` operation on that same durable `EpochAuthorityTransition` lineage.

ADR 0275 extends the ADR 0274 transition state machine with `source_resuming` and terminal `source_resumed`. Before either owner may adopt a fresh source pair, `source_resume` must win one expected-transition-version compare-and-set from `aborted` (or an equivalent fully drained pre-activation state) to `source_resuming`. That CAS is the linearization point against `aborted -> draining` retry and target activation. It binds an immutable source-resume intent containing at least the original source writer, old source pair, fresh source pair, cancellation-decision identity/digest, accountable opaque actor, purpose/reason code, policy/evidence version, and canonical intent digest. If retry wins the competing expected-version CAS, source-resume adoption count must remain zero and the cancellation controller must refresh authority before it can try again.

`source_resume` may enter `source_resuming` only when all of the following are true:

- the transition is the unique lineage for the exact source `(E,R)` and is in `aborted` or an equivalent fully drained pre-activation state;
- the source pair is still the authoritative current pair and the original source writer identity is unchanged;
- no target activation receipt exists and no target writer has acquired write authority;
- Organization and People ordinary admission receipts through their immutable source-boundary high-water marks are terminal;
- the transition-scoped reconciliation lane is closed and every recovery receipt through its high-water mark is terminal;
- the retiring-epoch work ledger is empty, every capacity-changing terminal outcome is applied, and Organization capacity backing is equivalent to authoritative People Assignment history;
- the most recent quiescence/discrepancy checks are recomputed from authoritative owner state for the current retry generation rather than reused from a predecessor generation; and
- the permanent-cancellation decision is purpose-bound, authenticated, policy-valid, and digest-bound to this exact transition and source-resume intent.

The old `(E,R)` admission gates are never reopened. The same source writer resumes under a fresh authority boundary `(E,R+1)`. `rollback_epoch` therefore acts as a monotonic generation of write authority inside one `authority_epoch`, including a governed return to the still-authoritative source writer when a target rollout is abandoned before activation. The fresh pair is part of the `source_resuming` intent and cannot be changed by an owner-local retry or contradictory controller.

Organization and People adopt `(E,R+1)` independently in owner-local transactions, but only while the transition is already `source_resuming` at the exact intent/version they observed. Each owner compare-and-sets its expected current authority/gate version while the old `(E,R)` business gate remains closed and emits an authenticated `SourceAuthorityAdoptionReceipt`. The receipt binds at least:

- transition identity, `source_resuming` state, source-resume intent digest, and expected transition version;
- owner context and source writer identity;
- old source pair `(E,R)` and new source pair `(E,R+1)`;
- the owner's immutable old closure-receipt identity and high-water digest;
- the newly installed authority/gate version;
- cancellation-decision identity/digest and policy/evidence version; and
- receipt identity, canonical payload digest, issuer, audience, tenant where applicable, signing-key version, and `domain_transition` purpose.

There is no cross-service SQL, shared transaction, or two-phase commit between Organization and People. One-sided adoption is not sufficient to reopen business admission. Until both adoption receipts are durable, authenticated, mutually consistent, and bound to the same `source_resuming` intent and fresh source pair, both owners remain fail closed for new HR business mutations.

While the lineage is `source_resuming`, retry, target activation, return to `aborted`/`draining`, creation of a second transition row for `(E,R)`, and creation of a successor transition from `(E,R+1)` all fail closed. Once either owner has committed fresh-pair adoption, recovery is roll-forward only through the same source-resume intent; an operator cannot restore availability by reverting one owner to `(E,R)` or by reviving the abandoned target.

After both adoption receipts are accepted, a single expected-transition-version CAS records an immutable `SourceAuthorityResumeReceipt` and moves the original rollover lineage from `source_resuming` to terminal state `source_resumed`. The receipt binds the two exact adoption receipt identities/digests and the immutable cancellation/source-resume intent. Only then may each owner open business admission for `(E,R+1)` by owner-local expected-gate-version CAS after verifying the terminal resume receipt. No request may ever obtain new `(E,R)` admission after the original closure.

`source_resumed` is terminal. The abandoned lineage cannot return to `draining`, cannot retry the abandoned target, and cannot produce an activation receipt. A later extraction, rollback, or writer transition starts a new `EpochAuthorityTransition` lineage from `(E,R+1)` with fresh owner-local admission closure receipts and high-water marks. Creation of that later lineage is permitted only after `source_resumed` is durable and both source-owner business gates report the fresh pair as open; partial source-resume finalization is not a valid new-transition source boundary.

All old `(E,R)` business receipts, closure receipts, drain proofs, reconciliation proofs, quiescence manifests, and abandoned-target artifacts remain immutable audit evidence. They are `audit_only` for future authority decisions: they cannot authorize new writes and cannot satisfy the closure or quiescence proof of a transition whose source pair is `(E,R+1)`.

## Concurrency and crash semantics

`source_resume` itself is idempotent and expected-version CAS protected. Equivalent controllers observe the same winning `source_resuming` intent, transition version, fresh pair, and eventual receipt identities. Contradictory fresh source pairs, writer identities, cancellation decisions, or payload digests fail closed.

A concurrent same-lineage retry and permanent-cancel request cannot both progress. Both operations race the same expected transition version before any owner-local source adoption. If retry wins `aborted -> draining`, the cancellation controller performs no adoption and may be reconsidered only after that generation again satisfies the full drain/reconciliation/settlement preconditions. If source resume wins `aborted -> source_resuming`, retry and target activation are rejected from that point forward; after any owner adoption, source resume is roll-forward only to `source_resumed`.

If the process crashes after the `source_resuming` CAS but before either owner adopts, replay verifies the exact intent and resumes owner-local adoption. It must not create a second source-resume intent or fall back to retry merely because no adoption receipt exists yet.

If one owner commits its `(E,R+1)` adoption and the other crashes before adoption, no new business admission opens on either side. The completed adoption receipt replays idempotently; recovery completes the missing owner adoption and then the transition-level resume CAS. Operators may repair availability, but they may not unilaterally reopen an owner gate, return the adopted owner to `(E,R)`, start target activation, or bypass the two-receipt barrier.

If the process crashes after both adoption receipts are durable but before the transition-level resume CAS, replay verifies both receipts and completes the same `SourceAuthorityResumeReceipt`. If it crashes after `source_resumed` but before an owner observes the terminal receipt, that owner may idempotently open only the already-installed `(E,R+1)` gate after verifying the terminal resume receipt. It may not infer resume from elapsed time or peer availability.

A controller that tries to create a new transition from `(E,R+1)` while the prior lineage is only `source_resuming`, or while either owner has not opened its fresh-pair business gate after `source_resumed`, fails closed. This prevents a successor transition from treating a partially finalized source-resume boundary as authoritative closure evidence.

## Alternatives rejected

Reopening `(E,R)` after abort is rejected because it creates source-pair ABA and makes old closure evidence ambiguous.

Deleting the aborted transition or creating a second transition for `(E,R)` is rejected because it breaks the one-source-pair/one-lineage invariant and can admit competing controllers.

Letting either owner adopt `(E,R+1)` before the transition first enters `source_resuming` is rejected because a concurrent retry can otherwise win after one-sided adoption and split the control plane.

Letting either owner reopen independently before terminal `source_resumed` is rejected because one-sided source availability can reintroduce cross-owner protocol work while the other owner still rejects the same authority pair.

Activating the abandoned target and then rolling back merely to restore source availability is rejected because it manufactures a dual authority transition and adds failure windows unrelated to the user's cancellation decision.

## Consequences and risk

Permanent cancellation can restore HR mutation availability without reusing old write authority or weakening the retirement barrier. The cost is a deliberate fail-closed window while the transition is `source_resuming`, both owners adopt the fresh source pair, and terminal resume evidence is finalized. Loss of one owner during that window can extend an outage, but the recovery action is to complete or repair adoption, not to bypass the barrier.

`rollback_epoch` consumers, signing-key manifests, receipt validators, audit export, and operability tooling must treat `(E,R+1)` as a fresh write-authority generation even though the source writer identity is unchanged. Old-epoch keys may remain verifiable for audit but cannot hold `domain_transition` authority for the fresh pair unless the released key manifest explicitly authorizes that pair.

The permanent-cancellation decision is an auditable control-plane decision, not a free-form operator toggle. The system retains only the minimum purpose-bound actor/policy/reason evidence required to explain and authorize the transition; HR payload and unrelated PII do not belong in source-resume receipts.

## Acceptance before ADR 0274/0275 can be Accepted

Executable two-owner/PostgreSQL evidence must prove at least these interleavings:

1. A fully drained `aborted` rollout is permanently cancelled; the transition first CASes to `source_resuming`, both owners adopt `(E,R+1)`, the original source writer regains HR mutation availability after terminal `source_resumed`, and target activation count remains zero.
2. Retry and permanent cancel start from the same `aborted` transition version. If retry wins, owner adoption count is zero. If source resume wins, retry generation does not advance and target activation remains permanently blocked.
3. Crash after `source_resuming` but before first owner adoption recovers the same immutable source-resume intent rather than creating a second intent or falling back to retry.
4. A new `(E,R)` business admission attempted after the original closure or after source resume fails closed.
5. Organization adopts `(E,R+1)` while People remains on closed `(E,R)`; neither owner reopens business admission, and retry/activation/reversion are rejected until People adoption and the terminal resume receipt are durable.
6. A stale `(E,R)` closure receipt, drain proof, or quiescence manifest is rejected as proof for a later transition sourced from `(E,R+1)`.
7. Concurrent retry and permanent-cancel controllers leave one transition state path: retry or `source_resuming -> source_resumed`, never both, with no target/source dual writer interval.
8. Duplicate and reordered adoption/resume receipts are idempotent only when byte-equivalent; mismatched writer, pair, transition version, cancellation decision, tenant, audience, key purpose, or digest fails closed.
9. Crash after one adoption, after both adoptions, and after `source_resumed` is recoverable without reopening `(E,R)`, creating a second source-pair lineage, or requiring cross-service SQL.
10. Attempting to create a successor transition from `(E,R+1)` before terminal `source_resumed` and both fresh-pair source gates are open fails closed. After that boundary, a later transition must create fresh closure receipts/high-water marks for `(E,R+1)`.
11. The resumed source path preserves the existing Employment/Assignment allocation and Position-capacity equivalence established before cancellation; source resume changes authority metadata, not HR domain facts.
12. Cancellation authorization with a stale policy version, wrong purpose, wrong transition/source pair, mismatched decision digest, or unauthorized actor fails before `source_resuming` and before any owner-local adoption.

The p95 buyer-path requirement remains <=20 ms where this control path intersects interactive mutation admission. Recovery orchestration itself is not hidden from measurement by synthetic warm-up or sample reduction; operational evidence records its distinct fail-closed availability window.

## Relationship to ADR 0274

ADR 0275 narrows one unresolved recovery gap in ADR 0274 and explicitly extends `EpochAuthorityTransition` with `source_resuming` and `source_resumed`. All ADR 0274 ownership, receipt-authentication, Employment-root serialization, predecessor-settlement, reconciliation, cutover, bitemporal migration, no-cross-service-SQL, and no-dual-writer rules remain in force. ADR 0274 and ADR 0275 must be reconciled into one executable state machine before either decision can become Accepted or authorize source extraction.
