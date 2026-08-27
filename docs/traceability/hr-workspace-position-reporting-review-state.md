# HR Workspace Position reporting review state traceability

Status: **active PR only**. This document does not claim protected-`develop` availability.

## Ownership and dependency boundary

- Shared protected-read accessibility owner: PR #130, `feat/hr-workspace-protected-read-state`.
- Authoritative Position reporting snapshot owner: PR #94.
- Reporting-line human review evidence owner: PR #95. Its review evidence does not apply a reporting mutation or authorize an employment decision.
- Durable reporting persistence owner: PR #106, dependency-first under #94. Persistence must independently enforce hierarchy integrity, tenant isolation, staffable Position coverage, audit/outbox evidence, and bitemporal truth.
- Descriptive Position span-of-control evidence owner: PR #133. It is structural workforce evidence, not a target span or employment-decision rule.
- This PR owns only the HR Workspace presentation/interaction state contract. It does not duplicate #94/#95/#106/#133 source, persistence, authorization, or decision logic.
- Figma design authority: `Orgmetra Baseline`, Storybook Inventory node `1:64`; required interaction states include default, focus, disabled, loading, validation-error, read-only, and high-risk-confirmation.

## Buyer-visible contract

The UI must make the next safe action explicit while keeping reporting-line review human-confirmed and non-authorizing:

| State | Buyer-visible meaning | Safe next action |
| --- | --- | --- |
| `idle` | No governed reporting evidence loaded | Load current Position/reporting evidence |
| `loading` | Fresh reporting evidence is being resolved | Wait; duplicate action disabled |
| `review` | High-risk human confirmation is required | Confirm subordinate/manager/hierarchy/staffable evidence |
| `recording` | Immutable review evidence is being recorded | Wait; duplicate submission disabled |
| `recorded` | Review evidence exists; reporting mutation has not occurred | Continue only through the authoritative reporting-line boundary |
| `denied` | Purpose/reviewer authority is insufficient | Review access purpose and reviewer authority |
| `stale` | Position/reporting evidence changed | Reload authoritative evidence |
| `blocked` | Cycle, duplicate-manager, self-report, or staffable-Position integrity is invalid | Resolve authoritative hierarchy integrity |
| `error` | Governed reporting/review service is unusable | Verify service and authorization; do not rely on cached evidence |

`review` and `recorded` must never imply that a reporting-line change has been applied. They do not authorize an employment decision.

## Privacy and data minimization

State evidence contains only bounded interaction semantics. It must not contain Person, Employment, or Assignment identifiers, worker names/contact information, compensation, ratings, assessment values, credentials/tokens, prompts, or model output.

## Verification

The dedicated `HR Workspace Position Reporting Review State Quality` workflow:

1. checks out the exact PR head;
2. runs Node.js 24 tests with 100% line, branch, and function coverage thresholds;
3. validates Figma correlation and Storybook state inventory;
4. verifies fail-closed runtime state handling and non-authorizing high-risk review semantics; and
5. requires a clean checkout.

Focused child evidence is stack-local. After #130 integrates, this child must be retargeted to fresh `develop` and all applicable browser/accessibility/Foundation/Recovery/SAST/Security/central controls must execute again. Parent checks and reviews do not transfer.
