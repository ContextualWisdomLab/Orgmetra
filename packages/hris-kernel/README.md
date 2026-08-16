# Orgmetra HRIS kernel

Pure tenant-scoped employment-truth rules for people, employment versions, positions, and assignments.

Use this package to:

1. Reconstruct one tenant's truth on an effective date and what Orgmetra knew at a recorded instant.
2. Reject an assignment that is not covered by the worker's same-tenant employment or a same-tenant staffable position.
3. Reject two exclusive jobs that share days inside one tenant, or a tenant seat whose visible allocations exceed 1.0000.
4. Reject a tenant-scoped allocation portfolio that exceeds 1.0000 for one employment.
5. Close a recorded interval and insert a replacement instead of rewriting history.

Every historical reconstruction and portfolio/capacity decision requires an explicit `tenant_record_id`. A colliding durable identifier from another tenant is ignored rather than treated as local employment truth.

This kernel does not talk to PostgreSQL, Keyverse, or any other service. Persistence and authorization stay at their adapter boundaries.
