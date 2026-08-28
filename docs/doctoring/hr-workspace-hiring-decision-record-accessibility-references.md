# Hiring decision record interaction and evidence references

Reviewed: 2026-08-28 (Asia/Seoul).

This note records primary standards used by the active Hiring decision record presentation slice. It is engineering/design evidence only. It does not claim WCAG certification, legal compliance, professional validation of a selection procedure, or authority for an autonomous hiring decision.

## Primary standards

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association. https://www.testingstandards.net/open-access-files.html

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures*, 29 C.F.R. Part 1607. https://www.eeoc.gov/regulations-and-guidelines

Society for Industrial and Organizational Psychology. (2018). Principles for the validation and use of personnel selection procedures. *Industrial and Organizational Psychology, 11*(S1), 1–97. https://doi.org/10.1017/iop.2018.195

World Wide Web Consortium. (2023, October 5). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/

World Wide Web Consortium. (2023, June 6). *Accessible Rich Internet Applications (WAI-ARIA) 1.2*. https://www.w3.org/TR/wai-aria-1.2/

## Design consequences

- A hiring decision is a high-impact accountable human action. The interaction requires explicit confirmation after the actor, purpose, reason, evidence version, criterion-linked evidence, and limitations are visible from authoritative governed sources.
- The presentation state never converts an assessment score, interview result, model output, or matching signal into decision authority. It also never creates an offer, Employment, or candidate-to-worker link.
- Recording is fail-closed: an in-progress submission is not treated as a recorded decision. Only the separately authoritative decision boundary plus immutable audit evidence can establish a recorded outcome.
- Recorded state is read-only. Corrections or downstream offer/hire actions must use their separately governed boundaries rather than mutating presentation state.
- Loading and recording expose `aria-busy` and disable duplicate actions. Denied, stale, evidence-blocked, and error states use alert semantics and provide a concrete next action.
- Generic interaction evidence is value-minimized and contains no candidate/Person identity, Job/requisition/application identifier, raw evidence, score, decision code/outcome, rating, compensation, credential, token, prompt, or model output.
- Interactive actions preserve visible `:focus-visible` treatment and a 44-pixel minimum target height using existing Orgmetra design tokens.
- Fresh Figma `Orgmetra Baseline` metadata was read on 2026-08-28. Recruiting Workspace node `1:22` names `Decision record with criterion evidence`; Storybook Inventory node `1:64` lists `DecisionRecord` and requires default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation states.

The active PR remains dependency-first. Focused child evidence is not shipped-product, legal-compliance, or selection-validity evidence.
