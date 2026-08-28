# Candidate evidence timeline accessibility references

Reviewed: 2026-08-28 (Asia/Seoul).

This note records primary accessibility design inputs for the active Candidate Evidence timeline interaction slice. It is engineering evidence, not a claim of WCAG certification or conformance for a deployed product.

## Primary standards

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Design consequences

- Loading is exposed through `aria-busy` and disables the repeated action while the governed read is in flight.
- Denied, stale, scope-blocked, and error states use assertive alert semantics and provide a concrete next action rather than silently widening access or relying on cached evidence.
- Read-only states remain visibly non-authorizing. They do not turn candidate evidence into ranking, rejection, progression, or employment-decision authority.
- The interactive action retains a visible `:focus-visible` treatment and a 44-pixel minimum target height using existing Orgmetra design tokens.
- The Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was freshly read on 2026-08-28 and continues to require default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation states. This slice uses that inventory as design correlation rather than creating parallel geometry.

The active PR must still be revalidated against fresh integrated parents and browser/accessibility evidence before its UI can be described as shipped.
