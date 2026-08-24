# Position reporting persistence — primary references

Checked against current final PostgreSQL 16 documentation on 2026-08-24. These references justify database mechanics only; they do not imply certification or a vendor-specific HR domain standard.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Constraints*. https://www.postgresql.org/docs/16/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Range/multirange functions and operators*. https://www.postgresql.org/docs/16/functions-range.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Aggregate functions*. https://www.postgresql.org/docs/16/functions-aggregate.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: ALTER TABLE*. https://www.postgresql.org/docs/16/sql-altertable.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function security*. https://www.postgresql.org/docs/16/perm-functions.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function volatility categories*. https://www.postgresql.org/docs/16/xfunc-volatility.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: System administration functions*. https://www.postgresql.org/docs/16/functions-admin.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Visibility of data changes*. https://www.postgresql.org/docs/16/spi-visibility.html

## Decision notes

- PostgreSQL row-security policies use `USING` for row visibility and `WITH CHECK` for inserted/updated rows; policies only apply when row security is enabled. Orgmetra therefore uses both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` on the two owned relationship relations, with a tenant-context policy. Production application roles must still be `NOSUPERUSER NOBYPASSRLS`.
- Exclusion constraints are appropriate for preventing two bitemporal versions under the same durable relationship identity from simultaneously overlapping in effective and recorded time. PostgreSQL range types provide half-open date/timestamp intervals for this purpose.
- PostgreSQL documents `range_agg(anyrange)` as the union of non-null input ranges returned as a multirange, and multirange containment supports asking whether that union contains one target range. Orgmetra uses this to prove that system-visible same-tenant `active`/`open` PositionVersion intervals cover the reporting relationship's entire effective range without iterating individual dates. The check also requires the stable Position anchor itself to be visible at the same recorded-time coordinate.
- Cross-row cycle detection cannot be expressed as an ordinary row-local `CHECK`. The migration uses a narrow PL/pgSQL insert guard over trusted Orgmetra-owned tables, explicit tenant predicates, and effective-period intersection. PostgreSQL function-security guidance is why the function does not use caller-controlled dynamic SQL or an unsafe mutable `search_path`.
- A single-session cycle check is insufficient under concurrent opposite mutations because each transaction could validate before the other commits. The trigger therefore takes a transaction-scoped advisory lock keyed from the tenant before querying the reporting graph. PostgreSQL documents that transaction advisory locks are held to transaction end, and that standard procedural `VOLATILE` functions execute their SQL commands in read-write SPI mode with a fresh snapshot for each query. Consequently, a waiter performs its graph lookup after the preceding lock holder commits and can observe/reject the newly created cycle. The dedicated concurrency regression proves this behavior against PostgreSQL rather than relying on the documentation alone.
- `FORCE ROW LEVEL SECURITY` is defense in depth, not an authorization substitute. Human-review and application evidence are separately bound into immutable audit/outbox correlation before a relationship version is accepted. The application event's `orgmetraevidence` is the reviewed-evidence digest, and the persisted application digest must equal the immutable audit envelope digest.
