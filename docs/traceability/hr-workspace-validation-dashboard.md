# HR Workspace Validation dashboard traceability

Status: **active PR evidence only**. This document does not change protected-main shipped truth or certify any selection procedure.

## Ownership boundary

- Parent PR #130 owns the shared HR Workspace protected-read interaction semantics and Figma/Storybook accessibility contract.
- This dependency-first child owns only the Validate / `ValidationMetric` presentation-state shell.
- Existing Orgmetra validity-study, criterion, Job-scope, selection-monitoring, and psychometric/statistical owners remain authoritative for their data and compute contracts. This UI does not duplicate a validity kernel, persistence boundary, monitoring service, candidate lifecycle, or employment-decision owner.
- Dedicated-writer CWL repositories remain read-only dependencies and are not mutated by this slice.

## Buyer-visible contract

The product baseline names a Validate surface and Figma `Orgmetra Baseline` Storybook Inventory node `1:64` lists `ValidationMetric`. This slice provides bounded executable states:

`idle / loading / ready / empty / denied / stale / scopeBlocked / error`.

`ready` is read-only governed evidence. It explicitly does not establish causality and does not rank, reject, advance, or authorize an employment decision. Every chart requires an exact-value table. `empty` means only that no governed validation evidence is visible inside the currently authorized scope. Denial, staleness, scope mismatch, and transport failure fail closed with a concrete next action.

The generic state payload intentionally contains no candidate/Person/Employment/Job/study identifiers, raw selection or assessment scores, validity coefficients, p-values, confidence intervals, adverse-impact ratios, ratings, compensation, credentials/tokens, prompts, or model output. Unsupported runtime values and prototype-inherited state names such as `constructor`, `toString`, and `__proto__` are rejected through exact primitive type plus own-key membership checks.

## Design and scientific evidence

Fresh Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was read on 2026-08-28 and still requires default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation behavior; it also states that exact-value tables accompany every chart. The implementation uses existing Orgmetra tokens and Storybook rather than parallel geometry.

WCAG 2.2, WAI-ARIA 1.2, the *Standards for Educational and Psychological Testing*, and SIOP's fifth-edition *Principles for the Validation and Use of Personnel Selection Procedures* are recorded under `docs/doctoring/hr-workspace-validation-dashboard-accessibility-references.md`. These references govern interpretation and interaction boundaries; they are not evidence that an individual study or procedure is valid.

## Verification contract

`.github/workflows/hr-workspace-validation-dashboard.yml` must:

1. check out and prove the exact candidate SHA;
2. use the reviewed Node 24 toolchain;
3. execute the focused interaction/privacy/fail-closed regression with exact 100% line, branch, and function coverage; and
4. finish with a clean checkout.

Contract-only head `2f6aec8940f557a3df93cb584648facfc068ab88` produced genuine hosted RED: run `33153931622`, job `98792136260` checked out and proved that exact SHA, set up Node 24.19.0, then failed at the focused contract with `ERR_MODULE_NOT_FOUND` because production `apps/hr-workspace/validation-dashboard-state.js` was intentionally absent.

Focused child GREEN is stack-local only. After #53 and #130 integrate, this child must be retargeted/reconciled against fresh `develop` and all applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflows must execute again on one resulting exact head. Parent or predecessor checks/reviews never transfer.
