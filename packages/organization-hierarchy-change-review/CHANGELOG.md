# Changelog

## 0.1.0 - Unreleased

- Add value-minimized `OrganizationHierarchyChangeReviewPacket` for reviewed Organization Unit parent changes.
- Preserve separate business-effective and system-recorded time, and reject future `recorded_at` values at issuance while keeping later evidence export independent of wall-clock freshness.
- Support real root attach/detach transitions without sentinel parent identifiers.
- Require same-purpose controlled reason evidence, distinct accountable requester/reviewer correlations, deterministic canonical JSON/SHA-256, redacted representation, and post-construction tamper detection.
- Reject caller-defined packet classes at subclass creation before they can override validation or attribute-resolution hooks, with an exact runtime check retained before any trust-bearing field read; this prevents checked-vs-emitted evidence substitution and `__post_init__` bypass.
- Bind each still-live tenant-qualified hierarchy-change reference to one evidence digest while permitting exact idempotent duplicates, preventing conflicting valid reissuance under the same review correlation.
- Normalize fixed-offset `recorded_at` values that cannot be represented as UTC to a governed validation error.
- Keep all packets fail-closed as human-review evidence only; authoritative same-tenant bitemporal re-resolution, stale-parent/cycle/multiple-parent checks, and immutable audit/outbox remain required before mutation.
- Add exact installed-wheel CPython 3.14.7 quality gating with 100% owned statement/branch coverage through canonical Foundation CI.
