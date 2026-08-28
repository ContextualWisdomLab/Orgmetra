# Employee profile Employment-history read — primary references

## Current authoritative references

National Institute of Standards and Technology. (2020). *Zero trust architecture* (NIST Special Publication 800-207). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207

National Institute of Standards and Technology. (2023). *A zero trust architecture model for access control in cloud-native applications in multi-cloud environments* (NIST Special Publication 800-207A). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207A

PostgreSQL Global Development Group. (2025). *PostgreSQL 18 documentation: Date/time types*. https://www.postgresql.org/docs/18/datatype-datetime.html

## Why these sources matter to PR #149

NIST SP 800-207 treats access to enterprise resources as an explicit authentication/authorization decision rather than an implicit consequence of network location. SP 800-207A extends granular identity-based enforcement to application and service boundaries. PR #149 applies that principle narrowly by authorizing the exact tenant, Person, purpose, operation, and requested Employment-history fields before protected retrieval.

PostgreSQL 18's date/time semantics support the repository's existing separation of business dates from timezone-aware system-recorded instants. The PR does not claim that PostgreSQL prescribes Orgmetra's bitemporal domain model; ADR 0003 remains the product architecture authority.

These references support the authorization and temporal representation boundaries only. They do not establish NIST certification, PostgreSQL conformance certification, or authority to infer attendance, fitness, compensation, performance, or an employment decision from Employment history.

## Review date

Rechecked as current final primary references on 2026-08-29. Re-review if NIST publishes a superseding final zero-trust application authorization specification or the protected repository changes its supported PostgreSQL major version.
