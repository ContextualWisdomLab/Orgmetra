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

`canonical_json()` is the exact compact UTF-8 persistence contract and `content_digest()` is SHA-256 over those exact bytes. An Orgmetra service writes both values to `audit_outbox_record` inside the same database transaction as its owning business mutation. Migration `0003_transactional_audit_outbox.sql` independently validates the event/tenant/governance envelope, rejects non-contract payload fields, recomputes the digest in PostgreSQL, forces tenant row-level security, and makes committed outbox evidence append-only. Delivery leases/retries are deliberately separate so transport progress cannot rewrite audit evidence.

This kernel does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries.
