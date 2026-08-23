# Employment-scoped base compensation references

Reviewed 2026-08-23 against current authoritative sources.

## APA 7 references

International Organization for Standardization. (2015). *ISO 4217:2015: Codes for the representation of currencies* (8th ed.). https://www.iso.org/standard/64758.html

PostgreSQL Global Development Group. (n.d.). *5.4. Constraints*. PostgreSQL 16 documentation. Retrieved August 23, 2026, from https://www.postgresql.org/docs/16/ddl-constraints.html

PostgreSQL Global Development Group. (n.d.). *8.17. Range types*. PostgreSQL 16 documentation. Retrieved August 23, 2026, from https://www.postgresql.org/docs/16/rangetypes.html

PostgreSQL Global Development Group. (n.d.). *9.9. Date/time functions and operators*. PostgreSQL 16 documentation. Retrieved August 23, 2026, from https://www.postgresql.org/docs/16/functions-datetime.html

PostgreSQL Global Development Group. (n.d.). *CREATE POLICY*. PostgreSQL 16 documentation. Retrieved August 23, 2026, from https://www.postgresql.org/docs/16/sql-createpolicy.html

## Design use

ISO 4217:2015 remains current and specifies the structure of a three-letter alphabetic currency code. Orgmetra uses that structural shape for `currency_code`; this PR intentionally does not freeze the mutable ISO assignment list into a CHECK constraint.

PostgreSQL exclusion constraints and range types are the authoritative database mechanism used to reject simultaneous effective-time/system-recorded-time truth for one Employment compensation anchor. PostgreSQL documents `transaction_timestamp()` as the start time of the current transaction and states that the value remains stable during that transaction; Orgmetra uses that database-owned coordinate both when a compensation knowledge interval opens (`recorded_from`) and when an existing open interval is closed (`recorded_to`). Compensation-specific triggers reject conflicting caller-authored coordinates before the generic bitemporal history guard permits the state transition. PostgreSQL row-level security policies are the database-level tenant visibility boundary applied independently to both new compensation relations.

These sources support database, temporal, and transport-shape decisions only. They do not establish compensation fairness, pay-equity conclusions, payroll compliance, tax treatment, or legal entitlement.