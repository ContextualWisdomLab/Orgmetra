# HR Workspace performance-goal review accessibility references

Status: active-PR evidence for the dependency-first HR Workspace performance-goal review interaction. This document does not claim protected-main integration or release authorization.

## Primary standards

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Applied contract

- In-flight load/record operations expose `aria-busy="true"` and disable duplicate action submission.
- Denied, stale, blocked, and error states use assertive alert semantics and always explain the next safe action.
- Interactive controls preserve the existing Orgmetra `:focus-visible` token and a minimum 44px target height.
- Human review is visually and semantically separated from authoritative activation. A recorded review is read-only evidence and cannot be interpreted as a performance rating, compensation action, or employment decision.
- Storybook evidence remains correlated to Figma `Orgmetra Baseline`, Storybook Inventory node `1:64`, whose required states are default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation.
