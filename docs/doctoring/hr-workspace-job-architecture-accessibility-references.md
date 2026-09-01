# Job Architecture workspace accessibility and evidence references

Status: **active PR evidence only**. This document does not describe protected-`develop` product truth and does not authorize Job, Position, Assignment, compensation, candidate, or employment-decision mutation.

## Product-design source

Orgmetra's Figma file `Orgmetra Baseline` (`xu1ZK1zmtFcDep95R8oE9O`) remains the product-design authority for this presentation slice. Fresh 2026-08-28 reads identify:

- Job Architecture frame `1:16`, which presents a versioned Job profile, Task → FJA → KSAO evidence, an evidence drawer, and publish-only-after-SME-review copy; and
- Storybook Inventory `1:64`, which requires default, hover/focus, disabled, loading, validation-error, read-only, and high-risk-confirmation behavior where applicable.

The executable state model correlates to those nodes but deliberately does not embed caller-controlled Job titles, identifiers, Task/FJA/KSAO values, sources, SME identities, prompts, or model output in generic interaction-state evidence.

## Accessibility decisions

- Loading and publication-in-progress states expose `aria-busy="true"` and disable the action that would otherwise duplicate the operation.
- Consequential SME confirmation uses an assertive alert state; ordinary read-only evidence uses a polite status state.
- Denied, stale, incomplete-evidence, and indeterminate-publication states fail closed and provide a concrete next action rather than implying success.
- The action target retains the existing Orgmetra 44-pixel minimum target size and shared `:focus-visible` focus-ring token.
- Published evidence is read-only and is asserted only after the separate authoritative Job Analysis boundary returns publication and immutable-audit evidence.
- Model-assisted Task/FJA/KSAO output remains untrusted draft evidence until accountable SME review. The workspace itself never ranks, rejects, or advances candidates and never grants compensation or employment-decision authority.

WCAG 2.2 is the current W3C accessibility Recommendation used for the interaction-level accessibility contract, while WAI-ARIA 1.2 defines the accessible-state vocabulary used here. O*NET's Content Model is used only as an external occupational-information reference corroborating the separation of task and worker-requirement evidence domains; O*NET does not become authoritative Orgmetra Job truth.

## APA 7 references

National Center for O*NET Development. (n.d.). *The O*NET Content Model*. O*NET Resource Center. Retrieved August 28, 2026, from https://www.onetcenter.org/content.html

World Wide Web Consortium. (2023). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

World Wide Web Consortium. (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/
