# Position lifecycle review traceability

## Truth state

- **Default-branch product truth:** `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` keeps Job, Position, and Assignment as distinct HRIS facts, owns Position lifecycle vocabulary, and carries purpose-bound authorization plus immutable audit/outbox foundations. It does not yet integrate this active PR's dedicated existing-Position lifecycle review artifact or authoritative lifecycle mutation.
- **Repository governance truth:** effective organization ruleset `18156473` applies to the default branch. The live payload requires one approving review, stale-review dismissal after push, review-thread resolution, extra approval for unattributed changes, seven central required workflows, and deletion/non-fast-forward protection; `require_last_push_approval` is currently false. Issue #89 owns the remaining governance/control-plane gap, including routine `OrganizationAdmin/always` bypass. These repository controls are not product capability and must be re-read before merge/release claims.
- **Active PR truth:** this branch adds only the governed review evidence packet and an exact-head installed-artifact/coverage contract consolidated under canonical Foundation CI.
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
| Exact owned test coverage without retired leaf CI | canonical Foundation delegates to `tests/test_position_lifecycle_review_artifact.sh`, which requires CPython 3.14.7, hash-bound isolated wheel installation, and the package's exact `--cov-branch --cov-fail-under=100` contract; `test_artifact_execution.py` rejects leaf-workflow resurrection |

## Buyer behavior

A buyer-facing workflow can collect a review of a proposed Position freeze/closure/abolition/reactivation without claiming the seat has changed. If the review outcome is rejected, the only next action is not to apply it. If approved for authoritative resolution, the next action explicitly requires fresh tenant-qualified Position/Assignment truth, actor authority/separation, staffing safety, evidence validation, and immutable audit/outbox before any mutation.
