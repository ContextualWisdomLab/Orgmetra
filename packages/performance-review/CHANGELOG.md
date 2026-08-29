# Changelog

## Unreleased

- Add a value-minimized, human-review-only performance-review evidence packet binding Employment/Job references while requiring downstream authoritative scope resolution before rating, together with performance cycle, criteria, goals, outcome evidence, optional development-plan provenance, and an accountable reviewer.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while namespaced packet-owned trust references require canonical non-sentinel UUIDv4-shaped values and reject UUIDv1/non-v4 suffixes. UUIDv4 syntax is no longer described as proof of opacity: until trusted issuer/resolver provenance verifies otherwise, independently supplied references are conservatively classified as potentially containing direct person identifier content.
- Restrict `reason_code` to the reviewed closed vocabulary (`scheduled_cycle_review`) so arbitrary lower-snake-case text cannot carry PII or ungoverned decision context into canonical evidence.
- Require exact built-in `str` values for every SHA-256 evidence digest before pattern validation and canonical binding, matching the strict runtime contract used by the other trust-bearing text fields.
- Bind a bounded positive `evidence_version` into canonical JSON and SHA-256 correlation evidence so high-impact review evidence versions are explicit and fail closed on invalid values.
- Make `generated_at` system-owned rather than caller-supplied: packet construction reads the trusted host clock, freezes it to a detached built-in UTC instant, rejects future/invalid clock results, and prevents callers from falsifying audit chronology by submitting arbitrary historical issuance times.
- Make the existing free-form-feedback exclusion machine-verifiable with immutable `contains_free_form_feedback=False` canonical evidence and fail-closed replacement validation, alongside the existing no-rating-value and no-free-form-model-output controls.
- Bind each live issued performance-review packet to its exact construction-time canonical bytes with a process-local HMAC seal stored outside packet-writable slots. Canonical export fails closed after valid-value post-issuance rewrites or when process-local issuance evidence is unavailable; durable uniqueness, authorization, and immutable audit/outbox remain authoritative host/persistence responsibilities.
