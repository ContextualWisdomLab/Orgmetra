# ADR 0018: Governed performance-review evidence packet

- Status: Proposed — active PR only
- Date: 2026-08-19

## Context

Orgmetra already owns authoritative Employment/Job truth and performance/criterion evidence boundaries, but a buyer-facing review workflow also needs a small pre-rating object that identifies which employment references, review period, performance cycle, criteria, goals, outcome evidence, and reviewer are being considered without copying rating values, narrative feedback, or model output into the envelope.

A transport-neutral packet cannot prove merely from syntactically valid references that the Person, Employment, Job, cycle, goals, and observation snapshot all resolve to one authoritative temporal scope. Nor can UUIDv4 syntax prove that independently supplied bytes were randomly generated or contain no encoded identifier content. Treating either relationship resolution or reference opacity as established from syntax would create a misleading high-impact evidence boundary. Authoritative relationship/temporal resolution and trusted reference-provenance verification therefore remain required downstream steps before rating. UUIDv1 is still rejected for packet-owned namespaced references because its timestamp/node layout is unnecessary metadata for this boundary. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package accepts the canonical non-sentinel operational UUID contract owned by that boundary rather than imposing a second version policy.

System-recorded time is also audit evidence. Accepting an arbitrary caller-supplied historical `generated_at` would let a caller backdate issuance while still passing a future-only validation gate. The packet therefore owns the issuance timestamp and reads it from the host clock during construction rather than accepting it as a public constructor or builder input.

U.S. OPM performance-management guidance treats performance management as a continuous cycle of planning, monitoring, developing, rating, and rewarding, and describes rating as evaluation against established elements and standards. ISO 30414:2025 Edition 2 provides current human-capital reporting requirements and recommendations across areas including productivity, skills/capabilities, and related workforce governance. Orgmetra uses those sources as design evidence, not as a claim that this packet by itself satisfies any jurisdiction-specific appraisal rule or ISO certification requirement.

## Decision

Introduce a transport-neutral `PerformanceReviewPacket` that remains pre-rating governance evidence.

The packet MUST bind:

- a canonical non-sentinel tenant identity under Orgmetra's authoritative operational UUID contract;
- canonical non-sentinel UUIDv4-shaped namespaced Person, Employment, Job, performance-cycle and performance-review references, rejecting UUIDv1 and other non-v4 suffixes without claiming that UUIDv4 syntax proves opacity;
- a governed criterion-set UUIDv4-shaped reference plus independent SHA-256 digest;
- a governed performance-goal-plan UUIDv4-shaped reference plus independent SHA-256 digest;
- an exact criterion-observation-snapshot UUIDv4-shaped reference plus independent SHA-256 digest;
- an optional development-plan UUIDv4-shaped reference/digest pair;
- explicit business review-period dates;
- one accountable UUIDv4-shaped reviewer, fixed `performance_review` purpose, and a reviewed closed reason code;
- a **system-owned** precision-preserving issuance timestamp read from the host clock inside the packet boundary, with no caller-supplied `generated_at` parameter; and
- a bounded positive integer `evidence_version`, defaulting to `1`, that is included in canonical evidence and therefore changes the packet digest when the governed evidence version changes.

The initial closed reason vocabulary contains only `scheduled_cycle_review`. Arbitrary lower-snake-case values are rejected even when syntactically well formed, because free-form reason text can encode a person name, identifier, or unreviewed decision context. Additional reasons require an explicit governed contract change and regression evidence before they can enter canonical review evidence.

`evidence_version` accepts only real integers from `1` through `2147483647`; booleans, text, zero, negative values, and overflow values fail closed. The field versions the immutable review evidence envelope and does not itself prove source-version resolution, human approval, or rating completion.

Because this package cannot prove independently supplied reference provenance, `contains_personal_data` and `contains_direct_person_identifiers` are both fixed to `True`. The latter is deliberately conservative: it means the envelope must be handled as potentially containing direct identifier content until an authoritative issuer/resolver verifies opacity. The packet MUST NOT carry a rating value, free-form feedback, or free-form model output. Direct construction and mutation-by-copy MUST fail closed unless `human_confirmation_required=True`, `decision_authority="human_review_only"`, `review_state="requires_human_review"`, and `scope_verification_state="requires_authoritative_resolution"` remain intact.

`scope_verification_state` deliberately cannot be changed to `verified` inside this package. Before rating, the authoritative HRIS/performance boundary must verify reference provenance and opacity, then resolve the Person↔Employment↔Job relation, performance-cycle/review-period alignment, and governed evidence scope using current temporal truth and purpose-bound authorization. UUIDv4 shape alone is not provenance evidence; tenant UUID generation/version/privacy policy likewise remains owned by the authoritative HRIS boundary.

`generated_at` is constructed from a trusted internal clock adapter. The resulting exact built-in timezone-aware `datetime` is normalized once to UTC and then sealed; future instants, missing/raising offsets, normalization overflow, datetime subclasses, or post-construction non-UTC reinjection fail closed. Tests may replace the internal clock adapter to make canonical bytes deterministic, but production callers cannot provide the issuance timestamp.

Canonical JSON and SHA-256 are immutable correlation evidence only. They do not prove the correctness of source evidence, authoritative cross-record scope, substantive validity or fairness of a criterion, lawful use, human completion, reference provenance, or the final rating.

## Consequences

Buyers can present a review-ready correlation envelope while keeping authoritative Employment/Job and performance evidence separable from the later human rating/feedback event. A consumer cannot truthfully treat the packet itself as proof that all referenced records belong to the same employee/job/cycle or that UUIDv4-shaped values are opaque. Until authoritative provenance verification occurs, the packet receives the more restrictive identifier-risk classification rather than a false no-direct-identifier assertion.

The system-recorded timestamp can no longer be backdated through public packet construction. Hosts still own purpose-bound authorization, durable immutable audit/outbox, retention/export controls, and the authoritative clock/runtime environment.

This slice adds no database migration, no rating computation, no cross-service table access, and no automated employment decision. The pre-rating packet preserves actor, purpose, reviewed reason, evidence version, conservative identifier-risk classification, and system-recorded issuance time in its immutable correlation evidence; later authoritative rating persistence must independently preserve those values plus human confirmation, audit/outbox, temporal scope, authoritative scope/provenance resolution evidence, and any applicable policy requirements.

## References

See `docs/doctoring/performance-review-references.md`.
