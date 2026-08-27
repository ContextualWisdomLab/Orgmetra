# HR Workspace Position lifecycle review state traceability

## Truth boundary

- This file is **active-PR evidence only** until the dependency stack integrates and is revalidated against fresh `develop`.
- Parent UI contract: PR #130 owns shared protected-read accessibility semantics and Figma/Storybook correlation.
- Position lifecycle governance owner: PR #111 owns the human-reviewed `PositionLifecycleChangeReviewPacket`; this UI does not recreate that evidence contract.
- Authoritative application owner: dependency-first PR #112 owns the later Position lifecycle mutation boundary. This UI does not write Position/Assignment truth and does not authorize an application.

## Buyer-visible requirement → evidence

| Requirement | Active-PR evidence | Safety meaning |
| --- | --- | --- |
| Load fresh Position and Assignment evidence before review | `loading` → `review` state model and Storybook stories | Cached or locally invented lifecycle truth is not presented as sufficient evidence. |
| Show a consequential review as explicit human confirmation | `review` uses `high-risk-confirmation` and a `Confirm lifecycle review` action | Confirmation records human review only; it does not apply, freeze, close, abolish, or reactivate a Position. |
| Prevent duplicate review recording | `recording` is busy and disables the action | One in-flight review recording is visible and duplicate submission is blocked in the interaction model. |
| Recorded review remains evidence only | `recorded` is read-only and disables the action | A completed review is not mutation authority. |
| Stale authoritative evidence fails closed | `stale` is an assertive validation alert | The reviewer must reload fresh authoritative Position and Assignment evidence before another review. |
| Staffing conflict fails closed | `blocked` is an assertive validation alert | The UI cannot override a staffing-safety boundary; fresh authoritative staffing evidence must be re-resolved. |
| Denied reviewer/purpose scope fails closed | `denied` is an assertive permission alert | No local or cached downgrade path is offered. |
| Service failure names a safe next action | `error` rejects cached review and instructs service/authorization verification | Customer-facing recovery copy does not fabricate evidence. |
| Figma/Storybook state inventory stays inspectable | every rendered state carries `data-figma-node-id="1:64"`; Storybook exposes nine named states | Reviewers can inspect default, loading, high-risk-confirmation, read-only, permission-denied, validation-error, error and focus-related evidence. |
| Owned interaction logic has exact coverage | focused workflow requires Node 24 100% line/branch/function coverage | Missing owned branches are non-passing. |

## Data minimization

The view model contains only constant governed copy and interaction semantics. It accepts no Person or candidate identity, worker name/contact data, compensation or salary values, ratings, assessment results, credentials or bearer tokens, prompts, model output, free-form HR notes, or Position/Assignment payload values.

## Consequential-decision boundary

A human confirmation in this UI is not a Position mutation and is not an employment decision. Before any authoritative change, the application boundary must freshly re-resolve same-tenant bitemporal Position and Assignment truth, the reviewed lifecycle evidence, staffing safety, actor separation/authority, effective/business time, system-recorded time, and immutable audit/outbox evidence. UI state never substitutes for those checks.

## Verification and stack discipline

The dedicated workflow runs the Position lifecycle interaction contract directly on Node 24, checks out the exact candidate head, requires exact 100% line/branch/function coverage, and proves a clean checkout. Parent #130, PR #111 and PR #112 checks/reviews never transfer to this child. After #130 actually integrates, retarget this child to fresh `develop`, reconcile any UI/design changes, and rerun every applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflow on one resulting exact head.
