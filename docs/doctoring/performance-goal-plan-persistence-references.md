# Performance goal-plan persistence — primary references

Reviewed 2026-08-26. These sources support the database mechanics used by active PR #125; they do not imply certification or product conformance beyond the tested Orgmetra contract.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.5. Constraints*. https://www.postgresql.org/docs/18/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: CREATE POLICY*. https://www.postgresql.org/docs/18/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 65.2. GiST indexes*. https://www.postgresql.org/docs/18/gist.html

## Decision relevance

PostgreSQL exclusion constraints provide the database-level mechanism used to reject overlapping bitemporal truth. GiST supplies the index access method supporting the range-overlap operators used by that constraint. Row-security policies provide `USING` and `WITH CHECK` predicates; Orgmetra additionally enables and forces RLS on both owned persistence relations and verifies tenant isolation through a `NOSUPERUSER NOBYPASSRLS` role.

These mechanics support, but do not replace, the higher-level Orgmetra requirements for human-reviewed activation provenance, immutable audit/outbox evidence, evidence minimization, and non-authorizing performance/employment decision states.
