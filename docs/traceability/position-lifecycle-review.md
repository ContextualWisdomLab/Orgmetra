# Position lifecycle review traceability

## Truth state

- **Default-branch product truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has distinct Job/Position/Assignment HRIS facts, Position status vocabulary, Position vacancy evidence dependencies, purpose-bound authorization, and immutable audit/outbox foundations. It can create Position records but has no dedicated lifecycle-change review artifact or authoritative existing-Position lifecycle mutation. Repository governance is separate: an **effective organization ruleset** applies to the default branch and requires pull-request integration, two approvals, stale-review dismissal, last-push approval, required conversation resolution, central required workflows, and non-fast-forward/deletion protection. Issue #89 tracks the remaining routine administrator `always` bypass and Orgmetra-local fail-closed gate-proof gaps.
- **Active PR truth:** this branch adds only the governed review evidence packet and its exact-head quality gate.
- **Planned:** authoritative bitemporal Position lifecycle mutation/persistence that consumes reviewed evidence, re-resolves staffing truth, and atomically records immutable audit/outbox.
- **Out of scope:** autonomous employment decisions, Person/candidate data, compensation, assessment/rating data, reporting-line mutation, Keyverse/Naruon/other CWL repository writes, and direct foreign application-table SQL.

## Requirement mapping

| Requirement | Evidence |
|---|---|
| Separate Position identity from lifecycle review evidence | `PositionLifecycleChangeReviewPacket`; ADR 0111 |
| Preserve business-effective and system-recorded time | `effective_on`, `reviewed_at`, `recorded_at`; chronology regressions |
| Human review with requester/reviewer separation | pseudonymous actor UUIDv4 correlations; separation regression |
| Purposefully non-authorizing high-impact evidence | fixed `human_reviewed`, `requires_authoritative_resolution`, `not_authorized_to_apply`, `human_review_only` states |
| Re-resolve staffing truth before mutation | reviewed Position/Assignment snapshot SHA-256 digests plus fixed approved next action |
| Minimize PII and high-impact payloads | packet carries no Person/candidate identity, allocation, compensation, rating, assessment, free text, credential, prompt, or model output |
| Fail closed on lifecycle ambiguity | explicit transition vocabulary; no-op rejection; abolished terminal; reason bound to target status |
| Tamper/correlation defense in depth | issuance digest verification; live tenant-qualified review-reference binding; adversarial `object.__setattr__` and `dataclasses.replace` regressions |
| Exact owned test coverage | `Position Lifecycle Review Quality` installed-wheel gate with `--cov-branch --cov-fail-under=100` |

## Buyer behavior

A buyer-facing workflow can collect a review of a proposed Position freeze/closure/abolition/reactivation without claiming the seat has changed. If the review outcome is rejected, the only next action is not to apply it. If approved for authoritative resolution, the next action explicitly requires fresh tenant-qualified Position/Assignment truth, actor authority/separation, staffing safety, evidence validation, and immutable audit/outbox before any mutation.
