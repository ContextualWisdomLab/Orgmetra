# ADR 0018: Governed performance-review evidence packet

- Status: Proposed — active PR only
- Date: 2026-08-19

## Context

Orgmetra already owns authoritative Employment/Job truth and performance/criterion evidence boundaries, but a buyer-facing review workflow also needs a small pre-rating object that proves which employment scope, review period, performance cycle, criteria, goals, outcome evidence, and reviewer are being considered without copying person values or prematurely materializing a rating.

U.S. OPM performance-management guidance treats performance management as a continuous cycle of planning, monitoring, developing, rating, and rewarding, and describes rating as evaluation against established elements and standards. ISO 30414:2025 Edition 2 provides current human-capital reporting requirements and recommendations across areas including productivity, skills/capabilities, and related workforce governance. Orgmetra uses those sources as design evidence, not as a claim that this packet by itself satisfies any jurisdiction-specific appraisal rule or ISO certification requirement.

## Decision

Introduce a transport-neutral `PerformanceReviewPacket` that remains pre-rating, value-free governance evidence.

The packet MUST bind:

- canonical tenant identity;
- opaque UUID-backed Person, Employment, Job, performance-cycle and performance-review references;
- a governed criterion-set reference plus independent SHA-256 digest;
- a governed performance-goal-plan reference plus independent SHA-256 digest;
- an exact criterion-observation-snapshot reference plus independent SHA-256 digest;
- an optional development-plan reference/digest pair;
- explicit business review-period dates;
- one accountable reviewer, fixed `performance_review` purpose, bounded reason code, and precision-preserving evidence timestamp.

The packet MUST NOT carry person PII, a rating value, free-form feedback, or free-form model output. Direct construction and mutation-by-copy MUST fail closed unless `human_confirmation_required=True`, `decision_authority="human_review_only"`, and `review_state="requires_human_review"` remain intact.

Canonical JSON and SHA-256 are immutable correlation evidence only. They do not prove the correctness of source evidence, the substantive validity or fairness of a criterion, lawful use, human completion, or the final rating.

## Consequences

Buyers can present a review-ready evidence envelope that keeps authoritative Employment/Job and performance evidence separable from the later human rating/feedback event. Person correlation remains sensitive metadata and therefore still requires purpose-bound access, least privilege, retention/export controls, and immutable audit handling.

This slice adds no database migration, no rating computation, no cross-service table access, and no automated employment decision. Later authoritative rating persistence must independently preserve actor, purpose, reason, evidence version, human confirmation, audit/outbox, temporal scope, and any applicable policy requirements.

## References

See `docs/doctoring/performance-review-references.md`.
