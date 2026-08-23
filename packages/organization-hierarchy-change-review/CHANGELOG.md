# Changelog

## 0.1.0 - Unreleased

- Add value-minimized `OrganizationHierarchyChangeReviewPacket` for reviewed Organization Unit parent changes.
- Preserve separate business-effective and system-recorded time, and reject future `recorded_at` values at issuance while keeping later evidence export independent of wall-clock freshness.
- Support real root attach/detach transitions without sentinel parent identifiers.
- Require same-purpose controlled reason evidence, distinct accountable requester/reviewer correlations, deterministic canonical JSON/SHA-256, redacted representation, and post-construction tamper detection.
- Bind each still-live tenant-qualified hierarchy-change reference to one evidence digest while permitting exact idempotent duplicates, preventing conflicting valid reissuance under the same review correlation.
- Keep all packets fail-closed as human-review evidence only; authoritative same-tenant bitemporal re-resolution, stale-parent/cycle/multiple-parent checks, and immutable audit/outbox remain required before mutation.
- Add exact installed-wheel CPython 3.14.7 quality gating with 100% owned statement/branch coverage.
