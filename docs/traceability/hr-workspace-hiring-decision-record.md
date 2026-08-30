# HR Workspace Hiring decision record traceability

Status: **active PR evidence only**. This document does not change protected-main shipped truth and does not authorize an employment decision.

## Ownership boundary

- Parent PR #130 owns the shared HR Workspace protected-read interaction semantics and Figma/Storybook accessibility contract.
- This dependency-first child owns only the Recruiting Workspace / `DecisionRecord` presentation and workflow-state shell.
- Existing Orgmetra selection-review/selection-decision evidence owners remain authoritative for decision evidence. Offer approval/response, confirmed-hire authority, People/Employment mutation, and candidate-to-worker conversion remain separate governed owners.
- This UI does not create a new selection algorithm, assessment owner, offer authority, hire authority, Employment mutation path, or candidate-to-worker linkage path.
- Dedicated-writer CWL repositories remain read-only dependencies and are not mutated by this slice.

## Buyer-visible contract

Protected PRD P1 names the Hiring decision record. Protected wireframes place the Selection decision record in Recruiting Workspace. Fresh Figma `Orgmetra Baseline` metadata identifies Recruiting Workspace node `1:22` with `Decision record with criterion evidence`, and Storybook Inventory node `1:64` lists `DecisionRecord`.

This slice provides bounded executable states:

`idle / loading / review / recording / recorded / denied / stale / evidenceBlocked / error`.

`review` is a high-risk-confirmation state. It requires an accountable human to verify criterion-linked evidence and limitations and explicitly confirm actor, purpose, reason, and evidence version. `recording` disables duplicate submission and is explicitly not proof of persistence. `recorded` is read-only and is asserted only after the authoritative decision boundary returns immutable audit evidence. No state itself creates an offer, Employment, or candidate-to-worker link.

Denied, stale, evidence-blocked, and error states fail closed with concrete next actions. Generic state payloads contain no candidate/Person identity, Job/requisition/application identifier, raw evidence, decision code/outcome, selection/assessment/interview score, rating, compensation, credential/token, prompt, or model output. Unsupported runtime values and prototype-inherited state names such as `constructor`, `toString`, and `__proto__` are rejected through exact primitive type plus own-key membership checks.

## Design and standards evidence

Fresh Figma `Orgmetra Baseline` metadata was read on 2026-08-28. Node `1:22` names the Recruiting Workspace decision record with criterion evidence. Storybook Inventory node `1:64` continues to require default, hover, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation behavior. The implementation reuses existing Orgmetra tokens and Storybook rather than creating a parallel design system.

WCAG 2.2, WAI-ARIA 1.2, the *Standards for Educational and Psychological Testing*, the Uniform Guidelines on Employee Selection Procedures, and SIOP's fifth-edition personnel-selection principles are recorded under `docs/doctoring/hr-workspace-hiring-decision-record-accessibility-references.md`. These sources constrain interaction and evidence interpretation; they are not evidence that an individual procedure or decision is valid or lawful.

## Verification contract

`.github/workflows/hr-workspace-hiring-decision-record.yml` must:

1. check out and prove the exact candidate SHA;
2. use the reviewed Node 24 toolchain;
3. execute the focused interaction/privacy/fail-closed regression with exact 100% line, branch, and function coverage; and
4. finish with a clean checkout.

Contract-only head `b721e46b11612733026139da0a41bb16293d77b7` produced genuine hosted RED: run `33162121276`, job `98818811945` checked out and proved that exact SHA, set up Node, then failed at the focused hiring-decision record contract while production `apps/hr-workspace/hiring-decision-record-state.js` was intentionally absent. The clean-checkout step was correctly skipped after the focused failure.

Focused child GREEN remains stack-local only. After #53 and #130 integrate, this child must be retargeted/reconciled against fresh `develop` and all applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflows must execute again on one resulting exact head. Parent or predecessor checks/reviews never transfer.
