# Employment absence persistence — primary references

Reviewed 2026-08-25. These sources support database mechanics only; they do not establish employment-law entitlement, certification, or a universal leave policy.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: ALTER TABLE*. https://www.postgresql.org/docs/18/sql-altertable.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: System administration functions—Advisory lock functions*. https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Constraints*. https://www.postgresql.org/docs/18/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Range/multirange functions and operators*. https://www.postgresql.org/docs/18/functions-range.html

## Design use

- `FORCE ROW LEVEL SECURITY` is used so table-owner access does not silently bypass the tenant policy in the intended constrained runtime path.
- The regression verifies a `NOSUPERUSER NOBYPASSRLS` reader because privileged roles can bypass row-security protections.
- Transaction-scoped advisory locks serialize the application-defined resource “one tenant-qualified Employment” while the overlapping-confirmed-absence invariant is checked. A hash collision can only serialize unrelated Employments; it does not authorize an otherwise-invalid insert.
- Range aggregation/containment is used to require full effective-interval coverage by current system-visible `active`/`leave` Employment versions, not merely a matching version at the absence start date.
- Exclusion constraints prevent contradictory bitemporal versions of one durable absence identity.
