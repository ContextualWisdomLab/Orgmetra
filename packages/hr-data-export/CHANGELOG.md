# Changelog

All notable package-local changes are documented here. Protected-repository release truth remains the root Orgmetra release process.

## 0.1.0 — Unreleased

### Added

- Value-minimized `HrDataExportReviewPacket` for pre-export HR data review.
- Reject future values for the system-recorded generation timestamp.
- Exact tenant/resource/authorization provenance correlation without HR field values.
- Explicit bounded field minimization, requester/reviewer separation, closed reason/format/destination vocabularies, and human-review-required state.
- UTC timestamp detachment from caller-controlled timezone providers and serialization-time integrity revalidation.
- Redacted representation plus deterministic canonical JSON/SHA-256 audit correlation.
- Adversarial tests and exact 100% owned statement/branch coverage gate.

### Security

- The packet is permanently `not_authorized_to_export` and `requires_authoritative_resolution`; it cannot itself be used as an export capability.
- Trust-bearing primitive subclasses and packet subclasses fail closed before governance comparisons or canonical serialization.
- Creation-time canonical evidence is sealed in a process-local weak registry outside packet-writable state so a low-level valid-looking post-issuance scope rewrite cannot become a second reviewed audit truth. Durable cross-process uniqueness and replay protection remain authoritative persistence responsibilities.
