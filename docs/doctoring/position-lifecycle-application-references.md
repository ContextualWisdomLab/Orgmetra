# Position lifecycle application — primary references

Reviewed 2026-08-24. These sources support database integrity, tenant isolation, and identifier semantics; they do not establish an employment-law rule or certification claim.

## APA 7 references

Davis, K., Peabody, B., & Leach, P. (2024). *Universally Unique IDentifiers (UUIDs)* (RFC 9562). RFC Editor. https://doi.org/10.17487/RFC9562

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Constraints*. https://www.postgresql.org/docs/16/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Function security*. https://www.postgresql.org/docs/16/perm-functions.html

## Design use

- RFC 9562 is the primary identifier source. Orgmetra continues to distinguish operational HRIS UUIDs from packet-owned UUIDv4 correlation identifiers.
- PostgreSQL row-security policy semantics support tenant-scoped `USING`/`WITH CHECK`; `FORCE ROW LEVEL SECURITY` is used for the new application evidence relation rather than claiming RLS is application authorization.
- PostgreSQL constraints and existing GiST bitemporal exclusions preserve non-overlapping effective/system-time truth. The lifecycle operation therefore closes the prior system-time interval and inserts a new effective segmentation rather than rewriting status in place.
- PostgreSQL warns that database functions can become privilege boundaries. This migration remains invoker-rights and schema-qualified for sensitive built-ins/relations where practical; it does not use a broad `SECURITY DEFINER` shortcut.