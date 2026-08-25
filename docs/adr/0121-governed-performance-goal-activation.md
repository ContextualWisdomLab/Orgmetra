# ADR 0121: Govern performance-goal activation as a separate authority boundary

Status: **Proposed — active stacked PR #121; not protected-main truth**

## Context

PR #92 defines reviewed performance-goal plan evidence, but intentionally does not make that evidence sufficient to activate a plan. A commercial HRIS/HCM system needs a clear boundary between “a human reviewed this proposed goal plan” and “the authoritative HR system accepted this exact plan for operational use.” Collapsing those states would let stale scope, a substituted actor, or changed evidence acquire operational meaning without fresh verification.

Performance-goal activation is not a performance rating and must not imply authority for compensation, promotion, discipline, separation, or another high-impact employment decision. The activation step must also remain independent of any future model-assisted drafting: model output is untrusted draft evidence only.

## Decision

Add a transport-neutral `activate_performance_goal_plan(...)` boundary in the existing `performance-goal-plan` package. It accepts only the exact governed `PerformanceGoalPlanPacket`, the same accountable reviewer identified by the reviewed packet, an approval instant that does not predate the reviewed evidence, and an injected `PerformanceGoalPlanActivationAuthority` owned by the Orgmetra host.

Before authority work, the function snapshots the parent packet's sealed canonical JSON and digest. The authority must freshly re-resolve and return exact-scope evidence for tenant, Employment, Job, performance cycle, goal-set digest, measurement-definition digest, feedback cadence, approving actor, approval instant, and its own immutable evidence reference/digest. Only the exact `PerformanceGoalPlanActivationVerification` runtime type is accepted.

After authority work, the parent packet's own creation seal is rechecked. An authority callback cannot rewrite the reviewed packet and have the changed object treated as the reviewed truth. The function then compares the authority snapshot with the pre-call plan snapshot and emits a value-minimized `PerformanceGoalPlanActivationReceipt` only on exact agreement.

The receipt is fixed to `authoritatively_activated`, `not_authorized_for_performance_rating`, and `not_authorized_for_employment_decision`. It contains correlation/provenance only; no goal text, rating, compensation value, assessment score, or free-form HR text. A process-local creation seal prevents low-level object rewriting from producing a second canonical receipt under the same object identity. This is defense in depth only; durable cross-process uniqueness, persistence, authorization, immutable audit/outbox, and later rating/decision workflows remain separate host responsibilities.

## Consequences

The design makes the high-impact transition explicit and testable without duplicating the authoritative HRIS data model or granting autonomous decision authority. It also keeps future persistence modular: a database adapter may persist the activation receipt only after the parent review lane and this activation lane integrate, and must re-establish tenant/system-time/audit guarantees at that boundary.

The activation package is intentionally stacked on #92. Parent checks or reviews do not transfer to #121. #92 must integrate first; the child must then be retargeted to fresh `develop` and all applicable current-head gates rerun before merge consideration.

## Evidence basis

Locke and Latham (2002) support preserving explicit goal-definition and feedback context rather than inferring performance quality from goal existence. NIST AI RMF 1.0 and its Playbook emphasize explicit human roles, responsibilities, oversight, documentation, and accountability when AI-enabled systems participate in organizational workflows. These sources support the separation of draft/review evidence, accountable human approval, and authoritative operational activation; they do not constitute certification or legal advice.
