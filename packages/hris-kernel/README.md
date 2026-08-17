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

`AuditOutboxEvent` fails closed on runtime type confusion, reserved nil UUID identities, ambiguous occurrence time, one-word/noncanonical source-service identifiers, malformed event types, free-text data placed in opaque-reference fields, noncanonical purpose/reason/result codes, whitespace-bearing evidence-version tokens, and missing confirmation for high-impact events. Source services use two-or-more-word `snake_case`; event types use the lower-case `orgmetra.<context>.<event>` namespace; resource, actor, and confirmation identifiers use namespaced opaque references rather than human-readable payload text.

`canonical_json()` is the exact deterministic JSON text that the owning service persists. `content_digest()` is SHA-256 over the UTF-8 bytes of that exact text. Callers must not independently serialize `to_cloudevent()` with library defaults and then assume the digest still addresses the stored representation. The Orgmetra PostgreSQL persistence boundary in migration `0003_audit_outbox_persistence.sql` reparses and allowlists that envelope, verifies tenant/event identity and high-impact confirmation, recomputes the digest over the supplied bytes, writes immutable `audit_event_record` evidence, and creates separate `outbox_delivery_record` transport state. The owning service calls `record_audit_outbox_event(...)` inside the same transaction as its business mutation.

This kernel itself does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries. Production dispatcher claiming, retry scheduling, lease-expiry recovery, retention/export, and external delivery receipts are not provided by the kernel and remain separately proven integration/operability work.
