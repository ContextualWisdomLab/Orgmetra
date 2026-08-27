# HR Workspace qualification-rule review state traceability

Status: **active PR only**. This document does not claim protected-`develop` availability.

## Ownership and dependency boundary

- Shared protected-read accessibility owner: PR #130, `feat/hr-workspace-protected-read-state`.
- Qualification-rule governance owner: PR #104 (`JobQualificationRuleReviewPacket`). Its review evidence remains `not_authorized_for_candidate_or_employment_decision`.
- Qualification-rule persistence owner: PR #105, dependency-first under #104. Persistence does not grant candidate-screening or employment-decision authority.
- This PR owns only the HR Workspace presentation/interaction state contract. It does not duplicate #104/#105 source, persistence, authorization, or decision logic.
- Figma design authority: `Orgmetra Baseline`, Storybook Inventory node `1:64`; required interaction states include default, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation.

## Buyer-visible contract

The UI must make the next safe action explicit while keeping qualification evidence human-reviewed and non-authorizing:

| State | Buyer-visible meaning | Safe next action |
| --- | --- | --- |
| `idle` | No governed qualification evidence loaded | Load current Job/Job Analysis evidence |
| `loading` | Fresh evidence is being resolved | Wait; duplicate action disabled |
| `review` | High-risk human confirmation is required | Confirm reviewed Task/KSAO/source evidence |
| `recording` | Immutable human-review evidence is being recorded | Wait; duplicate submission disabled |
| `recorded` | Review evidence exists; rule is not activated | Return to Job Analysis or a separately authorized authoritative boundary |
| `denied` | Purpose/reviewer authority is insufficient | Review access purpose and reviewer authority |
| `stale` | Job/Job Analysis evidence changed | Reload authoritative evidence |
| `blocked` | Required Task/KSAO/source scope is incomplete | Resolve governed evidence scope |
| `error` | Governed evidence/review service is unusable | Verify service and authorization; do not rely on cached evidence |

`review` and `recorded` must never imply that Orgmetra evaluated, ranked, rejected, or advanced a candidate. They do not authorize an employment decision.

## Privacy and data minimization

State evidence contains only bounded interaction semantics. It must not contain Person/candidate identifiers, names, contact information, raw qualification-rule text, assessment/cut scores, compensation values, credentials/tokens, prompts, or model output.

## Verification

The dedicated `HR Workspace Qualification Rule Review State Quality` workflow:

1. checks out the exact PR head;
2. runs Node.js 24 tests with 100% line, branch, and function coverage thresholds;
3. validates Figma correlation and Storybook state inventory;
4. verifies fail-closed runtime state handling; and
5. requires a clean checkout.

Focused child evidence is stack-local. After #130 integrates, this child must be retargeted to fresh `develop` and all applicable browser/accessibility/Foundation/Recovery/SAST/Security/central controls must execute again. Parent checks and reviews do not transfer.
