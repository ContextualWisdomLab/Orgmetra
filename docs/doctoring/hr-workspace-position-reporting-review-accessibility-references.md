# HR Workspace Position reporting review accessibility references

Status: **active PR research/doctoring**. These references support the interaction semantics; they are not a claim of product certification or protected-`develop` conformance.

## Applied decisions

- Use native button semantics and expose busy/live state explicitly so assistive technology can receive state changes without turning the review surface into a custom application widget.
- Keep the proposed reporting-line change behind an explicit high-risk human-confirmation state. UI confirmation records review evidence only; it does not mutate Position reporting truth or authorize an employment decision.
- Preserve a visible keyboard focus indicator and a minimum 44 CSS-pixel action height in the workflow-specific proof.
- Denial, stale-evidence, hierarchy-integrity, and error states use assertive alert semantics and always provide a concrete next action.
- Loading and recording disable duplicate submission while preserving a polite status announcement.

## Primary final standards

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

## Current-status note

WCAG 2.2 remains the completed W3C Recommendation used here and was approved as ISO/IEC 40500:2025; this slice does not claim ISO, WCAG, or accessibility certification. WAI-ARIA 1.2 remains the completed Recommendation used for roles, states, and properties. Later draft work is not treated as the normative production baseline for this slice.
