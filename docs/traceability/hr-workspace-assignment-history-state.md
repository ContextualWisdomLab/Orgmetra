# HR Workspace Assignment History interaction traceability

Status: **active PR only; not protected-main truth**.

## Buyer need

The PRD identifies Employee Profile with bitemporal Assignment history as a P1 HRIS surface. A customer needs to understand what Assignment evidence was effective and what Orgmetra knew at a selected system-knowledge coordinate without converting that read into mutation authority or leaking fields outside the authorized HR purpose.

## Ownership boundary

- PR #142 owns the separate purpose-bound People API Assignment-history read contract. Its active-PR backend evidence does not transfer into this UI lane.
- PR #130 owns the shared protected-read accessibility semantics and Figma/Storybook interaction system.
- This child owns **presentation/interaction only** for Assignment history. It introduces no Assignment writer, no cross-service SQL, and no dedicated-writer dependency mutation.

## Governed interaction evidence

`apps/hr-workspace/assignment-history-state.js` exposes only constant, value-minimized state semantics for `idle`, `loading`, `ready`, `empty`, `denied`, `stale`, `scopeBlocked`, and `error`.

The `ready` state explains the bitemporal distinction: effective time is when the Assignment fact applied; system-recorded time is when Orgmetra knew it. The state is read-only and cannot authorize Assignment mutation. `empty`, `stale`, and failure states prohibit inference outside the exact authorized business-time and known-at coordinate.

The view model intentionally carries no Person, Employment, Assignment, Job, Position, or Organization identifiers; worker names/contact data; compensation, rating, assessment, or candidate values; credentials/tokens; prompts; or model output. Actual authorized HR values remain backend response data and must be handled through purpose-bound field authorization rather than embedded in generic UI-state evidence.

## Design and accessibility evidence

Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was freshly re-read on 2026-08-28. The executable Storybook stories correlate to that node and reuse existing Orgmetra CSS tokens, visible `:focus-visible` treatment, loading semantics, read-only presentation, failure alerts, and 44px action target sizing. Current W3C WCAG 2.2 and WAI-ARIA 1.2 references are recorded under `docs/doctoring/hr-workspace-assignment-history-accessibility-references.md`.

## Executable acceptance

`tests/hr-workspace-assignment-history-state.test.mjs` requires:

- the full bounded state set and concrete next actions;
- read-only bitemporal explanation without mutation authority;
- no unsafe inference from empty/stale/scope-blocked/error states;
- exact built-in string state names and rejection of prototype-inherited names such as `constructor`, `toString`, and `__proto__`;
- Figma node correlation, Storybook inventory, existing focus/design tokens, loading/read-only/failure CSS states, and 44px action target; and
- exact 100% owned line, branch, and function coverage in the dedicated workflow.

After #53 and #130 integrate dependency-first, this child must be retargeted to fresh `develop`, reconciled with then-current Employee Profile and #142 backend truth, and rerun through applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflows. No parent or predecessor check/review transfers.
