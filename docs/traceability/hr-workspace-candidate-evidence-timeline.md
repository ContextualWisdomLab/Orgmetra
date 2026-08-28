# HR Workspace Candidate Evidence timeline traceability

Status: **active PR evidence only**. This document does not change protected-main shipped truth.

## Ownership boundary

- Protected `develop` already ships governed Candidate Evidence intake through merged PR #41. That backend packet is reference-only, purpose-bound, value-minimized, and not authorized for an employment decision.
- Parent PR #130 owns the shared HR Workspace protected-read interaction semantics and Figma/Storybook accessibility contract.
- This dependency-first child owns only the Candidate Evidence timeline presentation/interaction state model. It does not duplicate candidate intake, identity, requisition/Job authority, candidate lifecycle, selection decision, or evidence persistence.
- Dedicated-writer CWL repositories remain read-only dependencies and are not mutated by this slice.

## Buyer-visible contract

The Recruiting Workspace wireframe names a Candidate Evidence timeline. This slice provides bounded executable states for that surface:

`idle / loading / ready / empty / denied / stale / scopeBlocked / error`.

`ready` is read-only governed evidence. It explicitly does not evaluate, rank, reject, advance, or authorize an employment decision. `empty` means only that no evidence is visible inside the currently authorized scope. Denial, staleness, scope mismatch, and transport failure fail closed with a concrete next action.

The generic state payload intentionally contains no candidate/Person identifiers, names/contact data, requisition/Job identifiers, raw evidence or resume content, assessment/match values, ratings, compensation, credentials/tokens, prompts, or model output. Unsupported runtime values and prototype-inherited names such as `constructor`, `toString`, and `__proto__` are rejected through exact string plus own-key membership checks.

## Design and accessibility evidence

Fresh Figma `Orgmetra Baseline` Storybook Inventory node `1:64` was read on 2026-08-28 and still requires default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation behavior. The implementation uses existing Orgmetra tokens and Storybook rather than parallel geometry. WCAG 2.2 and WAI-ARIA 1.2 primary references are recorded in `docs/doctoring/hr-workspace-candidate-evidence-accessibility-references.md`.

## Verification contract

`.github/workflows/hr-workspace-candidate-evidence-timeline.yml` must:

1. check out and prove the exact candidate SHA;
2. use the reviewed Node 24 toolchain;
3. execute the focused interaction/privacy/fail-closed regression with exact 100% line, branch, and function coverage; and
4. finish with a clean checkout.

Focused child GREEN is stack-local only. After #53 and #130 integrate, this child must be retargeted/reconciled against fresh `develop` and all applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflows must execute again on one resulting exact head. Parent or predecessor checks/reviews never transfer.
