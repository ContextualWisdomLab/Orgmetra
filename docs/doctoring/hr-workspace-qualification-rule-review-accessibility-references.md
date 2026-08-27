# HR Workspace qualification-rule review accessibility references

Status: **active PR research/doctoring**. These references support the interaction semantics; they are not a claim of product certification or protected-`develop` conformance.

## Applied decisions

- Use native button semantics and expose busy/live state explicitly so assistive technology can receive state changes without converting the entire review surface into an application widget.
- Keep the high-impact qualification review as an explicit human-confirmation state. The state itself does not execute screening, ranking, rejection, advancement, or an employment decision.
- Preserve a visible keyboard focus indicator and a minimum 44 CSS-pixel action height in the workflow-specific proof.
- Error, denial, stale-evidence, and blocked-scope states use assertive alert semantics and always give a concrete next action.
- Loading and recording disable duplicate submission while preserving a polite status announcement.

## Primary final standards

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

## Scope note

WCAG 2.2 is the current completed W3C Recommendation used here for accessibility design guidance. WAI-ARIA 1.2 is the completed Recommendation used for roles, states, and properties; later ARIA work remains draft and is not treated as the normative production baseline for this slice.
