# HR Workspace legal-employer history interaction traceability

Status: **active PR only; not protected-main truth**.

## Buyer need

Employee Profile needs to explain which employing legal Organization is visible for an Employment at a selected business-time and system-knowledge coordinate without conflating legal-employer truth with Job, Position, Assignment, payroll, or statutory action. The read must remain useful to authorized HR users while minimizing generic UI-state evidence.

## Ownership boundary

- PR #130 owns the shared protected-read accessibility semantics and Figma/Storybook interaction system.
- PR #141 separately owns the active-PR authoritative bitemporal Employment → employing legal Organization relationship. Its backend evidence does not transfer into this UI lane and is not protected-main truth until integrated.
- This child owns **presentation/interaction only** for legal-employer history. It introduces no Employment or Organization writer, no cross-service application-table SQL, and no dedicated-writer dependency mutation.

## Governed interaction evidence

`apps/hr-workspace/legal-employer-history-state.js` exposes only constant, value-minimized state semantics for `idle`, `loading`, `ready`, `empty`, `denied`, `stale`, `scopeBlocked`, and `error`.

The `ready` state explains the bitemporal distinction: effective time is when the legal-employer relationship applied; system-recorded time is when Orgmetra knew it. It also states that employing legal Organization truth is independent of Position and Assignment. The state is read-only and cannot authorize Employment/Organization mutation, payroll action, or statutory action. `empty`, `stale`, and failure states prohibit inference outside the exact authorized business-time, known-at, and organization-scope coordinate.

The view model intentionally carries no Person, Employment, Organization, Position, Assignment, or candidate identifiers; organization/legal names; tax/jurisdiction/payroll values; worker contact data; compensation, rating, or assessment values; credentials/tokens; prompts; or model output. Actual authorized HR values remain governed backend response data and must be handled through purpose-bound field authorization rather than embedded in generic interaction-state evidence.

## Design and accessibility evidence

Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was freshly re-read on 2026-08-29 (Asia/Seoul). It continues to enumerate `Timeline`, `EmptyState`, `ErrorState`, `PermissionDenied`, and the required default/hover/focus/disabled/loading/validation-error/read-only/high-risk-confirmation vocabulary. This slice uses the existing Orgmetra design tokens, visible `:focus-visible` treatment, loading semantics, read-only presentation, failure alerts, and 44px action target sizing. WCAG 2.2 and WAI-ARIA 1.2 references are recorded under `docs/doctoring/hr-workspace-legal-employer-history-accessibility-references.md`.

## Executable acceptance

`tests/hr-workspace-legal-employer-history-state.test.mjs` requires:

- the full bounded state set and concrete next actions;
- read-only Employment/legal-Organization bitemporal explanation without mutation, payroll, or statutory authority;
- explicit independence from Position and Assignment;
- no unsafe inference from empty/stale/scope-blocked/error states;
- no generic-state PII, HR identifiers, legal/tax/payroll values, credentials, prompts, or model output;
- exact built-in string state names and rejection of prototype-inherited names such as `constructor`, `toString`, and `__proto__`;
- Figma node correlation, Storybook inventory, existing focus/design tokens, loading/read-only/failure CSS states, and 44px action target; and
- exact 100% owned line, branch, and function coverage in the dedicated workflow.

## Contract-first repair evidence

Contract head `b954b6330f5542b8c1272d4e2317c5ebf108e990` intentionally lacked the production state module. Hosted run `33219185795`, job `99009424985`, checked out and proved that exact SHA, configured Node 24.19.0, then failed at the focused contract with `ERR_MODULE_NOT_FOUND` for `apps/hr-workspace/legal-employer-history-state.js`. This is the realistic RED boundary for the buyer-visible slice; the subsequent implementation must obtain new exact-current-head GREEN evidence before the PR can advance.

After #53 and #130 integrate dependency-first, this child must be retargeted to fresh `develop`, reconciled with then-current Employee Profile and the integrated/then-current legal-employer backend truth, and rerun through applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflows. No parent or predecessor check/review transfers.
