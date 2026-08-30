# HR Workspace one-time export delivery accessibility references

Status: active-PR research evidence for the dependency-first HR Workspace export-delivery interaction slice. This note does not claim WCAG conformance, legal compliance, production deployment, or backend authorization.

## Design evidence reviewed

- Existing Figma `Orgmetra Baseline` file `xu1ZK1zmtFcDep95R8oE9O`, Storybook Inventory node `1:64`, reviewed read-only on 2026-08-27. The published inventory explicitly requires `default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation` states. This slice reuses that requirement and does not create new Figma geometry.
- Parent PR #130 owns shared protected-read loading/disabled/error/read-only/focus semantics and Orgmetra design-token usage. This child adds only one-time HR export-specific high-risk confirmation, delivered-receipt, and do-not-republish ambiguity behavior.

## Standards implications

WCAG 2.2 is a W3C Recommendation. The interaction proof is designed around keyboard-operable controls with visible `:focus-visible` treatment, clear labels/instructions, explicit error/denial next actions, and programmatically exposed status changes. The high-risk export flow deliberately keeps the delivery action disabled until a distinct confirmation state, and terminal delivery/indeterminate states keep republish disabled.

WAI-ARIA 1.2 is a W3C Recommendation used here only for interaction semantics. Non-urgent progress/read-only changes use `role=status` with polite live announcements; authorization denial and ambiguous delivery outcomes use `role=alert` with assertive announcements. `aria-busy=true` is reserved for the in-progress delivery state. These semantics do not substitute for backend authorization or immutable audit evidence.

## APA 7 references

World Wide Web Consortium. (2024, December 12). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/
