# Validation dashboard interaction and evidence references

Reviewed: 2026-08-28 (Asia/Seoul).

This note records primary standards used by the active Validation dashboard presentation slice. It is engineering/design evidence only. It does not claim WCAG certification, professional validation of any selection procedure, or that a dashboard summary establishes causal evidence.

## Primary standards

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association. https://www.testingstandards.net/open-access-files.html

Society for Industrial and Organizational Psychology. (2018). Principles for the validation and use of personnel selection procedures. *Industrial and Organizational Psychology, 11*(S1), 1–97. https://doi.org/10.1017/iop.2018.195

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Design consequences

- Validation evidence is presented as read-only evidence for accountable human interpretation; the UI does not convert a coefficient, interval, fairness metric, monitoring signal, or model-generated draft into selection or employment-decision authority.
- A chart never stands alone: the Figma `ValidationMetric` contract requires an exact-value table alongside every chart so the graphical encoding is not the sole carrier of magnitude or uncertainty evidence.
- The presentation explicitly avoids causal language. A descriptive or predictive association shown in a dashboard does not by itself establish a causal effect.
- Loading is exposed through `aria-busy` and disables duplicate requests while purpose-bound evidence is being resolved.
- Denied, stale, scope-blocked, and error states use alert semantics plus a concrete next action rather than widening scope, relying on cached evidence, or silently dropping unavailable evidence.
- Read-only state payloads are value-minimized: candidate/Person identifiers, raw scores, validity coefficients, p-values, intervals, fairness ratios, compensation, credentials, prompts, and model output are not embedded in generic interaction-state evidence.
- The interactive action retains a visible `:focus-visible` treatment and a 44-pixel minimum target height using existing Orgmetra design tokens.
- Fresh Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was read on 2026-08-28. It lists `ValidationMetric` and continues to require default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation states, with exact-value tables accompanying every chart.

The active PR must still be retargeted and revalidated after its parent integrates; focused child evidence is not shipped-product or statistical-validity evidence.
