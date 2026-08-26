# Employment work-capacity persistence — primary references

Reviewed 2026-08-26. These are implementation references, not claims of certification or regulatory compliance.

## Engineering conclusions

- PostgreSQL 18 defines `transaction_timestamp()` as the start time of the current transaction and keeps it stable throughout that transaction. Orgmetra therefore uses it as the system-recorded coordinate for one atomic capacity application instead of caller-supplied timestamps.
- PostgreSQL exclusion constraints are appropriate for preventing two system-visible versions from claiming the same tenant-qualified capacity identity and the same business `effective_on` while their recorded intervals overlap.
- Transaction-level advisory locks are held until transaction end. Orgmetra uses one application-defined key per tenant-qualified Employment so competing capacity applications serialize before current-capacity validation. A hash collision may reduce concurrency but does not permit contradictory state.
- PostgreSQL row-security policies apply `USING` to visible existing rows and `WITH CHECK` to new/updated rows when RLS is enabled. Orgmetra enables and forces RLS on the capacity anchor and version relations, with production tenant readers expected to use `NOSUPERUSER NOBYPASSRLS` roles.
- PostgreSQL cautions against cross-row `CHECK` constraints and recommends `UNIQUE`, `EXCLUDE`, foreign keys, or triggers for invariants involving other rows. Accordingly, Employment-state/current-capacity validation happens in the insert/application boundary rather than a cross-row `CHECK` expression.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.5 Constraints*. https://www.postgresql.org/docs/18/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.9 Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.9 Date/time functions and operators*. https://www.postgresql.org/docs/18/functions-datetime.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.28 System administration functions — Advisory lock functions*. https://www.postgresql.org/docs/18/functions-admin.html

## Boundary note

These PostgreSQL mechanics support integrity and temporal consistency. They do not establish reviewer authority, employment-law entitlement, payroll correctness, or suitability for work. Those remain separate governed HR boundaries. This PR also deliberately stores audit/outbox correlations as opaque contract evidence rather than querying another service's application tables.