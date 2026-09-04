# Orgmetra Job Grade Design Review

This package records **human-reviewed Job architecture evidence** for an enterprise-local grade and band proposal. It does not assign a grade, change compensation, mutate a Position or Assignment, or make an employment decision.

## What the packet binds

`JobGradeDesignReviewPacket` binds one tenant-scoped authoritative Job to one persisted Job Analysis snapshot and its SHA-256 digest, the reviewed Job-evaluation method and method digest, a proposed enterprise-local `grade_code` and `band_code`, the digest of the reviewed grade/band architecture definition, separated requester/reviewer actor correlations, a controlled review reason, explicit canonical `evidence_version = 1`, human review time, and later-or-equal system-recorded time.

The durable canonical evidence deliberately excludes Job title or task text, Person/worker/candidate identity, pay amounts, performance ratings, free-form explanations, prompts, model output, and credentials. Routine `repr()` is fully redacted.

## Authority boundary

Every packet is fixed to:

- `evidence_version = 1`
- `purpose_code = job_grade_design_review`
- `review_state = reviewed_for_authoritative_resolution`
- `decision_authority = not_authorized_to_assign_grade_or_compensation`
- `human_review_required = true`

The evidence version identifies the exact canonical review schema; a future incompatible schema requires an explicit versioned contract rather than caller-selected version inflation. The next authoritative boundary must re-read the same tenant Job, persisted Job Analysis snapshot, reviewed evaluation-method definition, and grade/band architecture; verify their evidence digests and reviewer authority; then persist any accepted Job-grade fact as bitemporal HRIS truth with immutable audit/outbox evidence. A packet never mutates Job, Position, Assignment, compensation, or an employment decision itself.

## Grade and band semantics

`grade_code` and `band_code` are separate enterprise-local normalized codes. This package intentionally does **not** impose universal grade ordering, compensation ranges, or U.S. federal General Schedule semantics. The `grade_band_definition_digest` binds whichever reviewed enterprise architecture defines those codes, so later authoritative persistence can detect stale or substituted definitions.

The ILO's gender-neutral Job evaluation guidance motivates using common, documented Job characteristics and an auditable evaluation method to reduce arbitrary or discriminatory valuation. U.S. OPM's Factor Evaluation System is retained only as a methodological example of explicit factors, levels, points, and conversion rules; Orgmetra does not adopt federal classification rules as an enterprise standard.

## Runtime integrity

Trust-bearing text must use exact built-in strings, accountable actor references use packet-owned opaque UUIDv4 correlations, authoritative tenant/Job/snapshot references reject reserved UUID sentinels, and evidence timestamps use exact built-in UTC datetimes. Canonical JSON is deterministic. `evidence_version` must be the exact built-in integer `1`; booleans, coercible values, unsupported versions, and integer subclasses fail closed.

A process-local weak issuance registry seals the creation-time digest outside packet-writable slots. If caller code bypasses the frozen dataclass and alters a field, later canonical evidence export fails closed. This is defense in depth only: durable uniqueness, authorization, tenant isolation, bitemporal persistence, and immutable audit/outbox remain responsibilities of the authoritative persistence transaction.

## Verification

The dedicated Job Grade Design Quality workflow executes the exact pull-request head, compiles source/tests, requires exact 100% owned production statement and branch coverage, and requires a clean checkout. Foundation, recovery, SAST, and security workflows remain separate repository-wide evidence and must also be terminal GREEN on the same head before review readiness is asserted.
