# Changelog

## [Unreleased]

### Added

- `CompensationChangeReviewPacket`, a value-minimized pre-mutation evidence contract that binds authoritative worker scope, reviewed compensation-plan/policy evidence, pay-equity review, budget authorization, and payroll handoff provenance without copying compensation or protected-attribute values.
- Fail-closed human-review, authoritative-resolution, no-HRIS-mutation, and no-payroll-execution states with separate requester/reviewer actor references and bounded evidence versions.
- Deterministic canonical JSON/SHA-256 evidence, redacted representations, canonical non-sentinel UUIDv4 identities for packet-owned namespaced opaque trust references, and exact 100% owned statement/branch coverage regressions.
- Creation-bound process-local evidence integrity: low-level valid-value field rewrites and unsupported object copies cannot emit a second valid-looking canonical compensation-review truth.
- Compensation-review quality now runs inside canonical `Foundation CI`; the package-specific workflow is retired after protected repository-quality consolidation, while the package `pyproject.toml` continues to enforce exact 100% statement and branch coverage.

### Changed

- `tenant_record_id` now follows the authoritative Orgmetra canonical non-sentinel operational-UUID contract instead of imposing a duplicate UUIDv4-only leaf policy; the protected-core UUIDv7 tenant form is covered explicitly while RFC 9562 Nil/Max sentinels remain rejected.
- Canonical export now snapshots all trust-bearing fields once and verifies the exact snapshot against the packet's construction-time SHA-256 seal before returning evidence. This process-local seal is defense in depth only and does not replace durable authorization, signatures, audit/outbox persistence, or correlation uniqueness.
- Digest evidence now rejects `str` subclasses so packet fields cannot retain caller-defined runtime behavior.
- Recorded-time evidence now resolves the input UTC offset once and stores a detached exact built-in UTC `datetime`; caller-owned mutable timezone state cannot rewrite or invalidate an already-issued packet, while indeterminate offsets and datetime subclasses fail closed.
