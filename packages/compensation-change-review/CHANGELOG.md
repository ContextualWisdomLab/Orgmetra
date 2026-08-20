# Changelog

## [Unreleased]

### Added

- `CompensationChangeReviewPacket`, a value-minimized pre-mutation evidence contract that binds authoritative worker scope, reviewed compensation-plan/policy evidence, pay-equity review, budget authorization, and payroll handoff provenance without copying compensation or protected-attribute values.
- Fail-closed human-review, authoritative-resolution, no-HRIS-mutation, and no-payroll-execution states with separate requester/reviewer actor references and bounded evidence versions.
- Deterministic canonical JSON/SHA-256 evidence, redacted representations, canonical non-sentinel UUIDv4 identity for `tenant_record_id` and namespaced opaque trust references that reject UUIDv1 timestamp/node correlation metadata, and exact 100% owned statement/branch coverage regressions.
