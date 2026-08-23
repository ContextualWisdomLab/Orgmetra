# Changelog

## 0.1.0 - Unreleased

- Add value-minimized `OrganizationHierarchyChangeReviewPacket` for reviewed Organization Unit parent changes.
- Preserve separate business-effective and system-recorded time.
- Support real root attach/detach transitions without sentinel parent identifiers.
- Require same-purpose controlled reason evidence, distinct accountable requester/reviewer correlations, deterministic canonical JSON/SHA-256, redacted representation, and post-construction tamper detection.
- Keep all packets fail-closed as human-review evidence only; authoritative same-tenant bitemporal re-resolution, stale-parent/cycle/multiple-parent checks, and immutable audit/outbox remain required before mutation.
- Add exact installed-wheel CPython 3.14.7 quality gating with 100% owned statement/branch coverage.
