# Traceability: Position-capacity source resume after permanent cancellation

## Authority

This document is executable acceptance planning for Proposed ADR 0275, which extends the Proposed ADR 0274 recovery state machine. It is not protected `develop` truth and does not authorize Position ownership extraction.

## Requirement-to-evidence map

| Requirement | RED interleaving | GREEN acceptance |
| --- | --- | --- |
| Never reopen the retired source pair | Begin with `(E,R)` Organization/People gates closed and a fully drained `aborted` rollover. Attempt a new business mutation using `(E,R)` during and after permanent cancellation. | Every new `(E,R)` admission fails. The only admissible resumed business authority is the fresh pair `(E,R+1)` after terminal source resume. |
| Two-sided fresh source adoption | Commit Organization adoption of `(E,R+1)` while People has not adopted it, then attempt Position/Assignment business mutations. | Both business lanes remain closed. No HR business mutation is admitted until both authenticated adoption receipts and the transition-level resume receipt are durable. |
| No source-pair ABA | Retain the old `(E,R)` closure receipt/high-water and attempt to use it as closure proof for a later migration starting from `(E,R+1)`. | Verification rejects the old receipt as source-boundary proof for the new lineage. It remains queryable only as immutable audit evidence. |
| One terminal path per lineage | Race an equivalent `aborted -> draining` retry controller against a permanent-cancel/source-resume controller using the same expected transition version. | Exactly one expected-version CAS wins. The loser refreshes and fails closed or follows the winner. A lineage never has both target activation and `source_resumed`. |
| No target activation after permanent cancel | Complete both source adoption receipts and source resume, then replay a previously valid target activation command/receipt. | Activation is rejected because `source_resumed` is terminal. Target activation count remains zero. |
| Crash-safe partial adoption | Crash after Organization has durably adopted `(E,R+1)` but before People adoption. | Organization does not reopen business admission. Replaying Organization adoption is idempotent; after People adopts the exact same pair, the transition can complete source resume without a second lineage or cross-service transaction. |
| Crash-safe finalization | Crash after both adoption receipts are durable but before `SourceAuthorityResumeReceipt`, then separately crash after terminal resume before one owner observes it. | First recovery verifies the two receipts and completes the same resume CAS. Second recovery opens only the already-installed `(E,R+1)` gate after verifying the immutable terminal resume receipt. |
| Receipt integrity and purpose | Replay adoption/resume receipts with changed source writer, old/new pair, transition version, tenant/audience, payload digest, or a valid historical key that is `audit_only` for `(E,R+1)`. | Every mismatch fails before domain mutation. Only byte-equivalent replay under a verification key authorized for the claimed pair and `domain_transition` purpose is idempotent. |
| Preserve HR domain truth | Start from settled Position backing and authoritative Assignment history, permanently cancel the rollout, resume the same source writer, and compare domain facts before/after. | Employment/Assignment/Position truth and effective occupancy are byte-/semantically equivalent apart from authority-control metadata and audit receipts. Source resume does not synthesize, rewrite, drop, clamp, or duplicate HR facts. |
| Restore availability without dual writer | Hold the target unactivated, complete source resume, and issue a normal HR mutation through the source writer. | Mutation succeeds only at `(E,R+1)`. There is no interval where the abandoned target and resumed source both possess write authority. |

## PostgreSQL concurrency fixture

The executable fixture uses separate Organization and People PostgreSQL connections plus an independent transition coordinator connection. Owner-local gate/adoption changes commit in separate database transactions. Tests must not replace this with one transaction spanning both owner schemas or a test-only cross-service SQL shortcut.

The fixture starts from an exact authoritative source pair `(E,R)`, a single `EpochAuthorityTransition`, durable Organization/People closure receipts and captured high-water marks, terminal ordinary drains, a closed/drained reconciliation lane, zero unresolved `commit_fenced` obligations, equivalent Organization backing/People Assignment history, and no target activation receipt.

For the retry-versus-cancel race, both controllers read the same transition version. A synchronization barrier releases their CAS attempts concurrently. Assertions require one state-path winner and prohibit a result where one controller increments retry generation while the other records source adoption/resume from the stale version.

For partial adoption, pause People before its owner-local adoption commit. Organization may persist its authenticated adoption receipt, but a concurrent business-admission request on either owner must remain blocked. Release People, verify the exact same fresh pair and source writer, then finalize one immutable resume receipt before admitting business work.

## Negative evidence

These observations are never sufficient to authorize source resume: elapsed time, absence of active database sessions, an empty queue sample, a current read that finds no Assignment, provider/gateway success, one owner's adoption receipt, an old quiescence manifest from another retry generation, or operator assertion without the durable transition and receipt evidence.

Administrator bypass, direct gate mutation, force-push, destructive rebase, and a second transition row for `(E,R)` are not test shortcuts. Tests must exercise the same fail-closed state machine intended for production.

## Performance and operability acceptance

Where authority validation is on an interactive Position/Assignment mutation path, measure real concurrent requests against the buyer-path p95 <=20 ms target. Report query, lock-wait, receipt-verification, connection-pool, and application-runtime components separately when the target is missed. Do not reduce contention samples, exclude slow failed-closed requests, or pre-warm an unrealistic cache to make the threshold pass.

Operational evidence must expose: source pair, transition identity/version/state, retry generation, both closure receipt digests/high-water marks, both fresh adoption receipt IDs/digests, terminal resume receipt ID/digest, target activation receipt absence, gate state for each owner, and the current `domain_transition` signing-key authorization. PII beyond tenant-qualified opaque domain identifiers is not required for this control-plane evidence.

## Release gate

ADR 0274 and ADR 0275 remain Proposed until these interleavings are executable on the canonical owner stack after prerequisite protected integration. Documentation review or synthetic state-machine examples alone are not distributed-correctness evidence. The implementation owner must preserve the same invariants through code, schema, API/receipt contract, security tests, recovery rehearsal, and normal protected-branch review/merge governance.
