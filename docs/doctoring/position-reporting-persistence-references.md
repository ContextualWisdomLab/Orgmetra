# Position reporting persistence — primary references

Checked against current final PostgreSQL 16 documentation on 2026-08-24. These references justify database mechanics only; they do not imply certification or a vendor-specific HR domain standard.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Constraints*. https://www.postgresql.org/docs/16/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Range/multirange functions and operators*. https://www.postgresql.org/docs/16/functions-range.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: ALTER TABLE*. https://www.postgresql.org/docs/16/sql-altertable.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function security*. https://www.postgresql.org/docs/16/perm-functions.html

## Decision notes

- PostgreSQL row-security policies use `USING` for row visibility and `WITH CHECK` for inserted/updated rows; policies only apply when row security is enabled. Orgmetra therefore uses both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` on the two owned relationship relations, with a tenant-context policy. Production application roles must still be `NOSUPERUSER NOBYPASSRLS`.
- Exclusion constraints are appropriate for preventing two bitemporal versions under the same durable relationship identity from simultaneously overlapping in effective and recorded time. PostgreSQL range types provide half-open date/timestamp intervals for this purpose.
- Cross-row cycle detection cannot be expressed as an ordinary row-local `CHECK`. The migration uses a narrow PL/pgSQL insert guard over trusted Orgmetra-owned tables, explicit tenant predicates, and effective-period intersection. PostgreSQL function-security guidance is why the function does not use caller-controlled dynamic SQL or an unsafe mutable `search_path`.
- `FORCE ROW LEVEL SECURITY` is defense in depth, not an authorization substitute. Human-review and application evidence are separately bound into immutable audit/outbox correlation before a relationship version is accepted.
