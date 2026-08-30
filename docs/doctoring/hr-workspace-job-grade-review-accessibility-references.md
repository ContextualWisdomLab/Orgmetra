# HR Workspace Job grade review accessibility references

Checked against current primary W3C publications on 2026-08-28. These references support interaction semantics only; they do not establish HR, compensation, or employment-decision authority.

## Design implications

- WAI-ARIA 1.2 defines `status` as advisory live-region information with implicit polite announcements and `alert` as assertive information that does not itself require focus. Orgmetra therefore uses `status` for ordinary progress/completion and `alert` for denial, stale evidence, and failure.
- WAI-ARIA 1.2 defines `aria-busy` as the state indicating that an element is being modified and assistive technologies may wait to expose updates. Orgmetra sets it only while loading or recording one governed review.
- WCAG 2.2 remains the current WCAG 2 Recommendation baseline. The UI preserves visible keyboard focus, a 44px minimum action target in the existing design-token system, actionable status copy, and no color-only state communication.
- The current 2026 WCAG 2 working-group activity includes proposed editorial/non-normative updates; those proposals are not treated as a replacement normative specification in this PR.

## APA 7 references

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

## Product boundary

The Storybook evidence correlates with the existing Figma `Orgmetra Baseline` Storybook Inventory node `1:64`. It is an active-PR design/test artifact and must not be presented as integrated protected-branch runtime until its dependency stack is merged and revalidated.
