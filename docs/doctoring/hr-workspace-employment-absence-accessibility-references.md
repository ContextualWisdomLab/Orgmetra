# HR Workspace Employment absence accessibility references

Status: **active stacked PR research/doctoring**. These references support the interaction semantics; they are not a claim of product certification, protected-`develop` availability, or compliance attestation.

## Applied decisions

- Use native button semantics and expose `aria-busy`, status/live-region, and alert semantics without turning the evidence surface into a custom application widget.
- Keep reason-free absence truth explicitly read-only. The UI may communicate that an Employment is absent or not absent at one reviewed business/system coordinate, but it must not disclose or infer medical, family, statutory, disciplinary, benefit, or free-form reasons.
- Do not infer attendance, availability, fitness for work, leave entitlement, scheduling, compensation, or employment-decision authority from absence truth.
- Disable duplicate submission while authoritative Employment/absence evidence is loading, and make loaded evidence read-only.
- Treat stale truth and tenant/Employment/Person/status/version inconsistency as fail-closed states with an explicit safe next action.
- Preserve a visible keyboard focus indicator and a minimum 44 CSS-pixel action height.
- Keep Storybook proof data value-minimized: no Person/Employment/Assignment identifiers, worker names/contact data, absence/leave reasons, medical/family/disciplinary data, compensation/benefit/rating/assessment values, credentials/tokens, prompts, or model output.

## Primary final standards

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

## Current-status note

WCAG 2.2 and WAI-ARIA 1.2 remain completed W3C Recommendations used as the normative accessibility baseline for this slice. Editorial or draft successor work does not replace those final standards here unless a future Orgmetra decision explicitly updates the baseline. This branch claims neither WCAG/ARIA conformance certification nor broader product accessibility certification.
