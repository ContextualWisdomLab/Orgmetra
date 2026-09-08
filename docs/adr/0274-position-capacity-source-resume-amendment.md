# ADR 0274 amendment: governed source resume after permanent rollover cancellation

## Status

Proposed — active PR only. This document amends the recovery state machine proposed in ADR 0274. It does not make ADR 0274 Accepted, does not authorize Position source extraction, and does not supersede the prerequisite integration order recorded there.

## Problem

ADR 0274 deliberately keeps the source `(authority_epoch=E, rollback_epoch=R)` business-admission gates closed after a retryable `aborted` transition. That is required so a retry can reuse the same immutable source-boundary closure receipts and high-water marks without source-pair ABA.

The same rule becomes a liveness failure when governance permanently abandons the target rollout before activation. The source writer is still authoritative, but both owners can remain unable to admit HR mutations indefinitely. Reopening the old `(E,R)` gates is not safe: work admitted after the original closure high-water would share an authority pair with evidence that already claims the pair was closed and drained.

Permanent cancellation therefore needs a distinct terminal recovery path. It is an authority-boundary transition, not a retry and not a rollback of HR domain facts.

## Decision

A retryable `aborted` transition continues to reserve its exact source pair and may only retry the byte-equivalent original target intent under ADR 0274. Permanent abandonment uses a separate `source_resume` operation on that same durable `EpochAuthorityTransition` lineage.

`source_resume` is permitted only when all of the following are true:

- the transition is the unique lineage for the exact source `(E,R)` and is in `aborted` or an equivalent fully drained pre-activation state;
- the source pair is still the authoritative current pair and the original source writer identity is unchanged;
- no target activation receipt exists and no target writer has acquired write authority;
- Organization and People ordinary admission receipts through their immutable source-boundary high-water marks are terminal;
- the transition-scoped reconciliation lane is closed and every recovery receipt through its high-water mark is terminal;
- the retiring-epoch work ledger is empty, every capacity-changing terminal outcome is applied, and Organization capacity backing is equivalent to authoritative People Assignment history;
- the most recent quiescence/discrepancy checks are recomputed from authoritative owner state for the current retry generation rather than reused from a predecessor generation.

The old `(E,R)` admission gates are never reopened. The same source writer resumes under a fresh authority boundary `(E,R+1)`. `rollback_epoch` therefore acts as a monotonic generation of write authority inside one `authority_epoch`, including a governed return to the still-authoritative source writer when a target rollout is abandoned before activation.

Organization and People adopt `(E,R+1)` independently in owner-local transactions. Each owner compare-and-sets its expected current authority/gate version while the old `(E,R)` business gate remains closed and emits an authenticated `SourceAuthorityAdoptionReceipt`. The receipt binds at least:

- transition identity and expected transition version;
- owner context and source writer identity;
- old source pair `(E,R)` and new source pair `(E,R+1)`;
- the owner's immutable old closure-receipt identity and high-water digest;
- the newly installed authority/gate version;
- receipt identity, canonical payload digest, issuer, audience, tenant where applicable, signing-key version, and `domain_transition` purpose.

There is no cross-service SQL, shared transaction, or two-phase commit between Organization and People. One-sided adoption is not sufficient to reopen business admission. Until both adoption receipts are durable, authenticated, mutually consistent, and bound to the same transition version and fresh source pair, both owners remain fail closed for new HR business mutations.

After both adoption receipts are accepted, a single expected-transition-version CAS records an immutable `SourceAuthorityResumeReceipt` and moves the original rollover lineage to terminal state `source_resumed`. Only then may each owner open business admission for `(E,R+1)`. No request may ever obtain new `(E,R)` admission after the original closure.

`source_resumed` is terminal. The abandoned lineage cannot return to `draining`, cannot retry the abandoned target, and cannot produce an activation receipt. A later extraction, rollback, or writer transition starts a new `EpochAuthorityTransition` lineage from `(E,R+1)` with fresh owner-local admission closure receipts and high-water marks.

All old `(E,R)` business receipts, closure receipts, drain proofs, reconciliation proofs, quiescence manifests, and abandoned-target artifacts remain immutable audit evidence. They are `audit_only` for future authority decisions: they cannot authorize new writes and cannot satisfy the closure or quiescence proof of a transition whose source pair is `(E,R+1)`.

## Concurrency and crash semantics

`source_resume` itself is idempotent and expected-version CAS protected. Equivalent controllers observe the same winning transition state and receipt identities. Contradictory fresh source pairs, writer identities, or payload digests fail closed.

A concurrent same-lineage retry and permanent-cancel request cannot both progress. Whichever operation first wins the expected-transition-version CAS defines the next state. If retry wins, cancellation refreshes the transition and may be reconsidered only after that generation again satisfies the full drain/reconciliation/settlement preconditions. If source resume begins or reaches `source_resumed`, retry and target activation are permanently rejected.

If one owner commits its `(E,R+1)` adoption and the other crashes before adoption, no new business admission opens on either side. The completed adoption receipt replays idempotently; recovery completes the missing owner adoption and then the transition-level resume CAS. Operators may repair availability, but they may not unilaterally reopen an owner gate or bypass the two-receipt barrier.

If the process crashes after both adoption receipts are durable but before the transition-level resume CAS, replay verifies both receipts and completes the same `SourceAuthorityResumeReceipt`. If it crashes after `source_resumed` but before an owner observes the terminal receipt, that owner may idempotently open only the already-installed `(E,R+1)` gate after verifying the terminal resume receipt. It may not infer resume from elapsed time or peer availability.

## Alternatives rejected

Reopening `(E,R)` after abort is rejected because it creates source-pair ABA and makes old closure evidence ambiguous.

Deleting the aborted transition or creating a second transition for `(E,R)` is rejected because it breaks the one-source-pair/one-lineage invariant and can admit competing controllers.

Letting either owner reopen independently is rejected because one-sided source availability can reintroduce cross-owner protocol work while the other owner still rejects the same authority pair.

Activating the abandoned target and then rolling back merely to restore source availability is rejected because it manufactures a dual authority transition and adds failure windows unrelated to the user's cancellation decision.

## Consequences and risk

Permanent cancellation can restore HR mutation availability without reusing old write authority or weakening the retirement barrier. The cost is a deliberate fail-closed window while both owners adopt the fresh source pair. Loss of one owner during that window can extend an outage, but the recovery action is to complete or repair adoption, not to bypass the barrier.

`rollback_epoch` consumers, signing-key manifests, receipt validators, audit export, and operability tooling must treat `(E,R+1)` as a fresh write-authority generation even though the source writer identity is unchanged. Old-epoch keys may remain verifiable for audit but cannot hold `domain_transition` authority for the fresh pair unless the released key manifest explicitly authorizes that pair.

## Acceptance before ADR 0274 can be Accepted

Executable two-owner/PostgreSQL evidence must prove at least these interleavings:

1. A fully drained `aborted` rollout is permanently cancelled; both owners adopt `(E,R+1)`, the original source writer regains HR mutation availability, and target activation count remains zero.
2. A new `(E,R)` business admission attempted after the original closure or after source resume fails closed.
3. Organization adopts `(E,R+1)` while People remains on closed `(E,R)`; neither owner reopens business admission until People adoption and the terminal resume receipt are durable.
4. A stale `(E,R)` closure receipt, drain proof, or quiescence manifest is rejected as proof for a later transition sourced from `(E,R+1)`.
5. Concurrent retry and permanent-cancel controllers leave one transition state path: retry or source resume, never both, with no target/source dual writer interval.
6. Duplicate and reordered adoption/resume receipts are idempotent only when byte-equivalent; mismatched writer, pair, transition version, tenant, audience, key purpose, or digest fails closed.
7. Crash after one adoption, after both adoptions, and after `source_resumed` is recoverable without reopening `(E,R)`, creating a second source-pair lineage, or requiring cross-service SQL.
8. The resumed source path preserves the existing Employment/Assignment allocation and Position-capacity equivalence established before cancellation; source resume changes authority metadata, not HR domain facts.

The p95 buyer-path requirement remains <=20 ms where this control path intersects interactive mutation admission. Recovery orchestration itself is not hidden from measurement by synthetic warm-up or sample reduction; operational evidence records its distinct fail-closed availability window.

## Relationship to ADR 0274

This amendment narrows one unresolved recovery gap in ADR 0274. All ADR 0274 ownership, receipt-authentication, Employment-root serialization, predecessor-settlement, reconciliation, cutover, bitemporal migration, no-cross-service-SQL, and no-dual-writer rules remain in force. If this amendment and ADR 0274 conflict, ADR 0274 remains Proposed and must be reconciled before either document can become Accepted.
