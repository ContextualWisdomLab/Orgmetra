# HR Workspace Employment work-capacity review accessibility references

Status: **active PR research/doctoring**. These references support the interaction semantics; they are not a claim of product certification, protected-`develop` availability, or compliance attestation.

## Applied decisions

- Use native button semantics and expose `aria-busy`, status/live-region, and alert semantics without turning the review surface into a custom application widget.
- Keep a proposed contracted work-capacity change behind an explicit high-risk human-confirmation state. UI confirmation records review evidence only; it does not mutate Employment truth or authorize compensation, scheduling, leave, payroll, or an employment decision.
- Disable duplicate submission while protected evidence is loading or immutable review evidence is being recorded.
- Treat stale Employment/terms/capacity-policy evidence and authoritative-scope inconsistency as fail-closed validation states with explicit next actions.
- Preserve a visible keyboard focus indicator and a minimum 44 CSS-pixel action height in the workflow-specific proof.
- Keep Storybook proof data value-minimized: no worker identifiers/contact data, capacity ratios, compensation/payroll values, leave reasons, ratings/assessment values, credentials/tokens, prompts, or model output.

## Primary final standards

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2* (W3C Recommendation). https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2* (W3C Recommendation). https://www.w3.org/TR/wai-aria-1.2/

## Current-status note

WCAG 2.2 remains the completed W3C Recommendation used as this slice's normative accessibility baseline. W3C continued editorial-errata work for WCAG 2.2 in 2026 without republishing the Recommendation, so this branch does not treat draft or proposed corrections as a replacement final standard. WAI-ARIA 1.2 remains the completed Recommendation used here for roles, states, and properties. This slice claims neither WCAG/ARIA conformance certification nor broader product accessibility certification.