# Orgmetra HRIS kernel

Pure tenant-scoped employment-truth and governed audit-envelope rules for people, employment versions, positions, and assignments.

Use this package to:

1. Reconstruct one tenant's truth on an effective date and what Orgmetra knew at a recorded instant.
2. Reject an assignment that is not covered by the worker's same-tenant employment or a same-tenant staffable position.
3. Reject two exclusive jobs that share days inside one tenant, or a tenant seat whose visible allocations exceed 1.0000.
4. Reject a tenant-scoped allocation portfolio that exceeds 1.0000 for one employment.
5. Close a recorded interval and insert a replacement instead of rewriting history.
6. Build a CloudEvents 1.0-compatible audit/outbox envelope that carries tenant, actor, purpose, reason, evidence version, result, and accountable human-confirmation references without copying mutable HR payload fields into a shadow system of record.

Every historical reconstruction and portfolio/capacity decision requires an explicit `tenant_record_id`. A colliding durable identifier from another tenant is ignored rather than treated as local employment truth.

`AuditOutboxEvent` requires timezone-aware occurrence time, lower-snake-case source-service identity, an `orgmetra.*` event type, nonblank governance references, and a confirmation reference for high-impact events. `content_digest()` provides a deterministic SHA-256 digest over the canonical structured envelope so persistence can detect later mutation. The caller must persist the envelope and digest atomically with the owning business write; this package deliberately does not pretend an in-memory object is a durable outbox.

This kernel does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries.