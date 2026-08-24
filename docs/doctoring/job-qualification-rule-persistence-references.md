# Job qualification-rule persistence references

Reviewed: 2026-08-24.

The sources below are design evidence only. Orgmetra does not claim that this feature establishes legal compliance, selection validity, federal qualification-policy conformance, or certification.

## APA 7 references

U.S. Office of Personnel Management. (n.d.). *Job analysis*. Retrieved August 24, 2026, from https://www.opm.gov/policy-data-oversight/assessment-and-selection/job-analysis/

U.S. Office of Personnel Management. (2022, May). *General Schedule qualification policies*. https://www.opm.gov/policy-data-oversight/classification-qualifications/general-schedule-qualification-policies/

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: CREATE POLICY*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: Constraints*. https://www.postgresql.org/docs/16/ddl-constraints.html

## Material design implications

- OPM treats job analysis as the documented link between job tasks/competencies and assessment or selection practice; qualification requirements should therefore retain exact Job Analysis provenance rather than become detached candidate-screening rules.
- OPM distinguishes minimum qualification standards from ranking or identifying the best-qualified applicant. Orgmetra therefore stores a reviewed rule artifact without granting candidate-ranking or employment-decision authority.
- PostgreSQL exclusion constraints support the single-valued bitemporal version contract, while row-security policies provide the database-level tenant visibility/check boundary used by the `NOSUPERUSER NOBYPASSRLS` application role.
