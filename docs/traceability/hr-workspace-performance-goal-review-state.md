# HR Workspace performance-goal review state traceability

Status: active stacked PR only; not protected-main truth and not release authorization.

| Need / risk | Owner boundary | Executable evidence |
| --- | --- | --- |
| Shared protected-read interaction semantics | #130 | Existing HR Workspace design tokens, focus treatment, loading/read-only/error patterns |
| Human-reviewed goal-plan governance evidence | #92 | Separate backend authority; this UI does not import or duplicate the unmerged implementation |
| Authoritative goal-plan activation | #121 | Separate backend authority; this UI never activates a plan |
| Durable goal-plan persistence | #125 | Separate persistence boundary; this UI stores no HR truth |
| Figma / Storybook interaction-state inventory | Figma `Orgmetra Baseline`, node `1:64` | Storybook stories and `data-figma-node-id="1:64"` correlation |
| Prevent review → activation/rating/compensation/employment-decision confusion | This PR | `review` and `recorded` state regressions explicitly deny those authorities |
| Prevent stale or inconsistent scope from becoming consequential action | This PR | `stale` and `activationBlocked` states require fresh authoritative evidence and governed owner resolution |
| Minimize UI-state evidence | This PR | View-model key allowlist excludes identifiers, goal text/value, ratings, compensation, assessments, credentials, prompts, and model output |
| Accessibility and actionable failure recovery | This PR | WCAG 2.2 / WAI-ARIA 1.2 doctoring, Storybook state inventory, exact 100% line/branch/function focused gate |

## Dependency-first integration

Base this slice on #130. Process #53 → #130 first. After the parent actually integrates, retarget/revalidate this child against fresh `develop`, reconcile intervening HR Workspace and performance-goal changes, and rerun every applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflow on one exact resulting head. Parent/backend checks and reviews never transfer.
