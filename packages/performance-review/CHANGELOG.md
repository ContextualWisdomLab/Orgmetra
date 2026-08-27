# Changelog

## Unreleased

- Add a PII-minimized, human-review-only performance-review evidence packet binding Employment/Job references while requiring downstream authoritative scope resolution before rating, together with performance cycle, criteria, goals, outcome evidence, optional development-plan provenance, and an accountable reviewer.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while namespaced packet-owned trust references remain canonical non-sentinel UUIDv4 and reject UUIDv1/non-v4 suffixes.
- Restrict `reason_code` to the reviewed closed vocabulary (`scheduled_cycle_review`) so arbitrary lower-snake-case text cannot carry PII or ungoverned decision context into canonical evidence.
- Require exact built-in `str` values for every SHA-256 evidence digest before pattern validation and canonical binding, matching the strict runtime contract used by the other trust-bearing text fields.
- Bind a bounded positive `evidence_version` into canonical JSON and SHA-256 correlation evidence so high-impact review evidence versions are explicit and fail closed on invalid values.
- Freeze `generated_at` to a detached built-in UTC instant at issuance, reject future instants, normalize mutable/raising/missing timezone providers to fail-closed validation, and prevent later caller timezone behavior from rewriting canonical performance-review evidence.
- Bind each live issued performance-review packet to its exact construction-time canonical bytes with a process-local HMAC seal stored outside packet-writable slots. Canonical export fails closed after valid-value post-issuance rewrites or when process-local issuance evidence is unavailable; durable uniqueness, authorization, and immutable audit/outbox remain authoritative host/persistence responsibilities.
