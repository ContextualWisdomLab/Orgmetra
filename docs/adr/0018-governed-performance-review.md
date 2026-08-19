# ADR 0018: Governed performance-review evidence packet

- Status: Proposed — active PR only
- Date: 2026-08-19

## Context

Orgmetra already owns authoritative Employment/Job truth and performance/criterion evidence boundaries, but a buyer-facing review workflow also needs a small pre-rating object that identifies which employment references, review period, performance cycle, criteria, goals, outcome evidence, and reviewer are being considered without copying person values or prematurely materializing a rating.

A transport-neutral packet cannot prove merely from syntactically valid opaque references that the Person, Employment, Job, cycle, goals, and observation snapshot all resolve to one authoritative temporal scope. Treating correlation as verified scope would create a misleading high-impact evidence boundary. Authoritative relationship and temporal resolution therefore remains a required downstream step before rating.

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
- one accountable reviewer, fixed `performance_review` purpose, a reviewed closed reason code, and precision-preserving evidence timestamp.

The initial closed reason vocabulary contains only `scheduled_cycle_review`. Arbitrary lower-snake-case values are rejected even when syntactically well formed, because free-form reason text can encode a person name, identifier, or unreviewed decision context. Additional reasons require an explicit governed contract change and regression evidence before they can enter canonical review evidence.

The packet MUST NOT carry person PII, a rating value, free-form feedback, or free-form model output. Direct construction and mutation-by-copy MUST fail closed unless `human_confirmation_required=True`, `decision_authority="human_review_only"`, `review_state="requires_human_review"`, and `scope_verification_state="requires_authoritative_resolution"` remain intact.

`scope_verification_state` deliberately cannot be changed to `verified` inside this package. Before rating, the authoritative HRIS/performance boundary must resolve the Person↔Employment↔Job relation, performance-cycle/review-period alignment, and the governed evidence scope using its current temporal truth and purpose-bound authorization.

Canonical JSON and SHA-256 are immutable correlation evidence only. They do not prove the correctness of source evidence, authoritative cross-record scope, substantive validity or fairness of a criterion, lawful use, human completion, or the final rating.

## Consequences

Buyers can present a review-ready correlation envelope while keeping authoritative Employment/Job and performance evidence separable from the later human rating/feedback event. A consumer cannot truthfully treat the packet itself as proof that all referenced records belong to the same employee/job/cycle. Person correlation remains sensitive metadata and therefore still requires purpose-bound access, least privilege, retention/export controls, and immutable audit handling.

This slice adds no database migration, no rating computation, no cross-service table access, and no automated employment decision. Later authoritative rating persistence must independently preserve actor, purpose, reason, evidence version, human confirmation, audit/outbox, temporal scope, authoritative scope-resolution evidence, and any applicable policy requirements.

## References

See `docs/doctoring/performance-review-references.md`.
