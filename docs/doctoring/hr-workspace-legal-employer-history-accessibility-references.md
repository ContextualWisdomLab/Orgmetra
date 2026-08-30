# HR Workspace legal-employer history accessibility references

Reviewed: 2026-08-29 (Asia/Seoul)

This note records design and accessibility inputs for the active legal-employer-history interaction slice. It is engineering evidence, not a claim of accessibility certification, employment-law compliance, payroll compliance, or statutory compliance.

## Primary standards

World Wide Web Consortium. (2024, December 12). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

World Wide Web Consortium. (2025, October 21). *Web Content Accessibility Guidelines (WCAG) 2.2 approved as ISO/IEC international standard*. https://www.w3.org/press-releases/2025/wcag22-iso-pas/

## Applied consequences

- Loading is perceivable through `aria-busy=true`, and transient status updates use a polite live region.
- Permission, stale-evidence, organization-scope, and transport failures use assertive alert semantics and provide a concrete next action.
- Keyboard focus remains visible through the existing Orgmetra focus token; actionable controls preserve a 44px minimum target height.
- Loaded legal-employer history remains explicitly read-only. UI evidence does not grant Employment or Organization mutation authority, payroll authority, statutory authority, or consequential employment-decision authority.
- The legal-employer relationship is described independently of Position and Assignment so presentation does not collapse distinct HRIS entities.
- Empty and stale states prohibit inference beyond the exact authorized business-time, system-knowledge, and organization-scope coordinate.
- Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was freshly re-read on 2026-08-29 and continues to enumerate Timeline, EmptyState, ErrorState, PermissionDenied, and the default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation interaction vocabulary. This slice reuses that design system rather than introducing parallel geometry or tokens.
