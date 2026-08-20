# Changelog

All notable package changes are recorded here.

## Unreleased

- Add a governed, aggregate-only `SelectionOutcomeMonitoringPlan` that binds one Job-scoped total selection process to exact aggregate population/outcome snapshots, protected-attribute handling, small-sample interpretation, statistical-plan provenance, a distinct accountable reviewer, and explicit human review without carrying candidate-level values or making an adverse-impact/legal determination.
- Require the public `tenant_record_id` and every namespaced trust-bearing reference to use canonical non-sentinel UUIDv4 identity, rejecting UUIDv1 timestamp/node correlation metadata as well as human-readable, value-bearing, sentinel, noncanonical, and other non-v4 reference suffixes through construction and replacement paths.
- Require every packet reference to be re-resolved within the exact tenant through its authoritative boundary before actor separation, Job-scope verification, or accountable review, preventing cross-tenant evidence mixing behind valid opaque UUIDs.
- Bind a true positive `evidence_version` (1..2147483647) into canonical JSON and SHA-256 evidence so revisions to high-impact monitoring evidence cannot silently collide.