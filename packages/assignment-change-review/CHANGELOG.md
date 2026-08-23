# Changelog

## Unreleased

### Added

- Governed pre-mutation assignment-change review packet with exact opaque HRIS/evidence references, deterministic SHA-256 correlation, requester/reviewer separation, mandatory human review, and an explicit not-authorized-to-apply state.
- Exact workforce-allocation policy reference/digest binding alongside current-scope, allocation-plan, worker-impact, and communication evidence.
- Canonical non-sentinel UUIDv4 identity for every packet-owned namespaced trust reference, rejecting UUIDv1 timestamp/node correlation metadata and other UUID versions.
- Bounded positive `evidence_version` in canonical evidence so high-impact actor/purpose/reason evidence remains explicitly versioned.
- Tenant-scoped pre-approval re-resolution of every packet reference plus Person-to-Employment-to-current-Assignment and current worker-scope verification in the governed next action.
- Fail-closed prevention of Person PII, compensation values, free-form model output, noncanonical references, malformed evidence digests, free-form sensitive reason metadata, invalid evidence versions, and direct-construction governance bypasses.
- Issuance-time normalization of `generated_at` to a detached built-in UTC instant, with rejection of future instants and fail-closed handling of mutable, missing, raising, or overflowing timezone providers so canonical evidence cannot change after issuance through caller-owned timezone behavior.

### Changed

- `tenant_record_id` now follows protected Orgmetra's authoritative canonical non-sentinel operational-UUID contract rather than a duplicate UUIDv4-only leaf policy; the core UUIDv7 tenant form is accepted while RFC 9562 Nil/Max sentinels remain rejected.
