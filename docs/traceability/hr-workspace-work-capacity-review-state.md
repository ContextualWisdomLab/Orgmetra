# HR Workspace Employment work-capacity review state traceability

Status: **active stacked PR**. This document records the presentation/interaction contract owned by this branch. It does not claim protected-`develop` availability, accessibility certification, or authority to mutate Employment truth.

## Ownership boundary

- Parent presentation contract: #130 `feat/hr-workspace-protected-read-state@b3b30058a79174000919d566fbbb1fdad80c62bf`.
- HR Workspace product parent: #53.
- Governed Employment work-capacity review evidence: #103. This branch does not import or duplicate that unmerged backend implementation.
- Durable Employment work-capacity persistence: #128. This branch does not write its tables or bypass its future authoritative mutation boundary.
- Employment leave/separation workflows remain separate governed concepts; this UI must not infer leave, scheduling, payroll, compensation, or employment-decision authority from a work-capacity review.
- Figma correlation: `Orgmetra Baseline`, Storybook Inventory node `1:64`, freshly read on 2026-08-28. The node requires `default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation` states and an exact-value table alongside chart evidence where charts exist. This slice uses only the interaction-state inventory; it does not invent a parallel design system.

## State-to-governance mapping

| UI state | Interaction proof | Governance meaning | Required next action |
| --- | --- | --- | --- |
| `idle` | default | No governed evidence has been loaded. | Load fresh Employment, terms, and capacity-policy evidence. |
| `loading` | loading + disabled | Protected evidence resolution is in progress. Duplicate action is blocked. | Wait for the governed load to complete. |
| `review` | high-risk confirmation | Human review only. No Employment, compensation, scheduling, leave, or employment-decision mutation authority. | Confirm the reviewed scope and evidence before recording the review. |
| `recording` | loading + disabled | Immutable review-evidence recording is in progress; duplicate submission is blocked. | Wait for recording to complete. |
| `recorded` | read-only | Review evidence exists; no work-capacity change has been applied. | Continue only through a separately authorized authoritative work-capacity boundary after fresh validation. |
| `denied` | permission denied | Purpose or reviewer authority is insufficient. | Correct the purpose/authority before retrying. |
| `stale` | validation error | Employment, terms, capacity-policy, or reviewed evidence changed. | Reload authoritative evidence before reviewing again. |
| `blocked` | validation error | Current capacity, effective date, Employment status, or reviewed policy evidence is inconsistent. | Resolve authoritative scope conflicts before retrying. |
| `error` | error | Governed evidence/review service did not return a usable result; cached evidence is not accepted. | Verify service and authorization, then retry the governed load. |

## Privacy and integrity contract

The Storybook proof is deliberately value-minimized. Its immutable view-model vocabulary contains only presentation semantics (`ariaBusy`, `ariaLive`, `role`, `submitDisabled`, `interactionState`, `actionLabel`, `label`, `message`, `nextAction`). It must not carry Person/Employment/Assignment identifiers, worker names/contact data, current or proposed capacity ratios, compensation/payroll values, leave reasons, ratings/assessment scores, credentials/tokens, prompts, or model output.

The state input is an exact built-in string drawn from a finite vocabulary. Caller-defined boxed/string-like runtime objects fail closed before rendering. Static proof markup is correlated to Figma node `1:64`, preserves visible focus semantics, exposes busy/live-region state, uses native button semantics, and enforces a minimum 44 CSS-pixel action height.

## Verification

The dedicated `HR Workspace Work Capacity Review State Quality` workflow is intentionally scoped to this presentation slice and its documentation. It checks out the exact PR head, runs Node.js 24 tests with exact 100% line/branch/function coverage, and requires a clean checkout. This focused evidence is **stack-local** only. It does not inherit #53/#130 or #103/#128 reviews/checks and does not substitute for browser/accessibility/Foundation/Recovery/SAST/Security/central required workflows after integration.

## Integration order

Process #53 -> #130 first. After #130 integrates, retarget this child to fresh `develop`, reconcile any parent changes without transferring predecessor evidence, and rerun every applicable exact-head browser/accessibility/Foundation/Recovery/SAST/Security/central gate. High-impact UI confirmation remains review evidence only until an authoritative backend independently revalidates tenant/scope, actor separation, effective time, policy/evidence freshness, and immutable audit/outbox requirements.