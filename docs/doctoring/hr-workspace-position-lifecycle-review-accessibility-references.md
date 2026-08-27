# HR Workspace Position lifecycle review accessibility references

Checked against the current W3C Recommendation baselines used by the existing HR Workspace interaction stack. These references support interaction semantics only; they do not establish Position mutation, staffing, or employment-decision authority.

## Design implications

- WAI-ARIA 1.2 defines `status` as advisory live-region information and `alert` as assertive information that does not itself require focus. Orgmetra therefore uses `status` for ordinary load/review/recording progress and `alert` for denial, stale evidence, staffing conflicts, and failures.
- WAI-ARIA 1.2 defines `aria-busy` for content that is being updated. Orgmetra sets it while loading authoritative evidence or recording one human review, and the action is disabled to prevent a duplicate interaction.
- WCAG 2.2 remains the normative WCAG Recommendation baseline used here. The interaction preserves visible keyboard focus, a 44px minimum action target in the existing design-token system, actionable non-color-only state copy, and explicit next actions.
- The Figma `Orgmetra Baseline` Storybook Inventory node `1:64` explicitly requires `default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation` states. This slice implements those semantics for a Position lifecycle review without inventing a new geometry or application authority.

## APA 7 references

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

## Product boundary

High-risk confirmation in this Storybook evidence records the need for accountable human review; it does not execute a Position lifecycle mutation. PR #111 remains the review-evidence owner and PR #112 remains the authoritative application owner. Before consequential application, fresh bitemporal Position/Assignment evidence and staffing safety must be re-established by the authoritative Orgmetra boundary.
