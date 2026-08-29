# Job grade persistence primary references

Review date: 2026-08-24.

## APA 7 references

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Constraints*. https://www.postgresql.org/docs/16/ddl-constraints.html

U.S. Office of Personnel Management. (n.d.). *Classification & qualifications: Factor Evaluation System grade determination*. https://www.opm.gov/policy-data-oversight/classification-qualifications/

## Design consequences

PostgreSQL row-level security requires RLS to be enabled for policy enforcement; this lane additionally uses FORCE RLS and tests visibility through a `NOSUPERUSER NOBYPASSRLS` role. PostgreSQL exclusion constraints provide the overlap primitive used to reject simultaneously effective/system-visible competing Job-grade versions for one Job assignment anchor.

OPM Factor Evaluation System material demonstrates an auditable factor-level/point-to-grade methodology. Orgmetra uses that only as methodological evidence for reviewed method/provenance binding. It does **not** adopt U.S. federal factor definitions, point tables, GS grades, legal classification rules, or OPM authority as an enterprise grading standard.

These references are engineering inputs, not certification, legal advice, Job-evaluation validity evidence for a particular employer, or authorization to assign compensation or make employment decisions.
