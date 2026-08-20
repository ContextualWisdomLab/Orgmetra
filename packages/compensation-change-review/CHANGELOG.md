# Changelog

## [Unreleased]

### Added

- `CompensationChangeReviewPacket`, a value-minimized pre-mutation evidence contract that binds authoritative worker scope, reviewed compensation-plan/policy evidence, pay-equity review, budget authorization, and payroll handoff provenance without copying compensation or protected-attribute values.
- Fail-closed human-review, authoritative-resolution, no-HRIS-mutation, and no-payroll-execution states with separate requester/reviewer actor references and bounded evidence versions.
- Deterministic canonical JSON/SHA-256 evidence, redacted representations, canonical non-sentinel UUIDv4 identities for packet-owned namespaced opaque trust references, and exact 100% owned statement/branch coverage regressions.

### Changed

- `tenant_record_id` now follows the authoritative Orgmetra canonical non-sentinel operational-UUID contract instead of imposing a duplicate UUIDv4-only leaf policy; the protected-core UUIDv7 tenant form is covered explicitly while RFC 9562 Nil/Max sentinels remain rejected.
