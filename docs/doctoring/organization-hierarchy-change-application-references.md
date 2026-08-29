# Organization hierarchy-change application references

Reviewed 2026-08-25 against PostgreSQL 18 current documentation. These sources support database behavior used by active PR #119; they do not establish that #119 is integrated, released, or certified.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 13.3. Explicit locking*. Retrieved August 25, 2026, from https://www.postgresql.org/docs/18/explicit-locking.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.28. System administration functions*. Retrieved August 25, 2026, from https://www.postgresql.org/docs/18/functions-admin.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: CREATE POLICY*. Retrieved August 25, 2026, from https://www.postgresql.org/docs/18/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 9.9. Date/time functions and operators*. Retrieved August 25, 2026, from https://www.postgresql.org/docs/18/functions-datetime.html

## Decision relevance

- PostgreSQL documents advisory locks as application-defined and voluntary. Transaction-level advisory locks are automatically released when the transaction ends. Orgmetra therefore uses them to serialize its own tenant hierarchy mutation boundary but does not treat them as a replacement for RLS, privileges, constraints, or auditing.
- `CREATE POLICY` documents `USING` for existing-row visibility and `WITH CHECK` for new/updated rows. The application evidence relation enables and forces RLS and uses tenant scope for both expressions.
- PostgreSQL documents `transaction_timestamp()` as the start time of the current transaction and explicitly notes that it remains unchanged during the transaction. PR #119 therefore includes a regression for an older transaction that attempts to apply reviewed hierarchy evidence after a later-started hierarchy mutation commits, plus a database guard that requires a fresh transaction rather than allowing the earlier cutoff to reconstruct stale graph truth.
- PostgreSQL foreign-key and deferred-constraint semantics support the application-first/successor-later write order. PR #119 combines tenant/unit-qualified version keys with a deferred reverse binding, and exercises direct cross-unit, missing-successor, malformed-JSON, and future-effective-cycle failures in the PostgreSQL contract.
