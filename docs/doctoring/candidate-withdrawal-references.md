# Candidate withdrawal primary-source references

## Scope note

These sources inform the design of Orgmetra's governed candidate-withdrawal boundary. They do not establish certification or conformance, and none of them is interpreted as prescribing Orgmetra's exact physical schema. The implementation remains an Orgmetra-owned product decision.

## Design findings

### Digital identity and authentication

NIST SP 800-63-4 is the current final Digital Identity Guidelines revision (July 2025) and covers identity proofing, authentication, federation, and related assertions. SP 800-63B-4 is the companion final publication focused on authentication and authenticator management. For this slice, the material design consequence is that an identifier such as `candidate:<opaque-id>` must not be treated as proof that the current claimant is that candidate. Orgmetra therefore keeps identity/authentication verification at the authorized adapter boundary and persists a reference/digest to the resulting identity-resolution evidence rather than pretending that actor-string syntax authenticates a person.

This PR does not assign an Identity Assurance Level, Authenticator Assurance Level, or Federation Assurance Level and makes no NIST conformance claim.

### Event interoperability

The CloudEvents project lists v1.0.2 as the latest released core CloudEvents specification. Orgmetra's existing audit/outbox persistence already uses a CloudEvents-compatible version-1.0 envelope with product-specific governance extensions. Candidate withdrawal reuses that accepted envelope and binds the exact withdrawal subject, candidate actor, identity-resolution reference/digest, withdrawal evidence reference/digest, evidence version, purpose, reason, time, and result rather than inventing a second event format.

### PostgreSQL persistence controls

PostgreSQL 16 `CREATE POLICY` documentation specifies that row-level security policies become effective after RLS is enabled and that `USING` controls visible rows while `WITH CHECK` controls proposed rows. The candidate-withdrawal relation follows the repository's existing FORCE-RLS tenant-context pattern and tests it using a `NOBYPASSRLS` role.

PostgreSQL 16 `CREATE TRIGGER` documentation defines BEFORE row triggers as executing before the attempted row operation and supports TRUNCATE triggers. Orgmetra uses a BEFORE INSERT governance trigger to re-resolve local application/audit evidence and separate UPDATE/DELETE/TRUNCATE rejection triggers to preserve append-only withdrawal history.

## APA 7 references

Cloud Native Computing Foundation. (2022). *CloudEvents specification* (Version 1.0.2). GitHub. https://github.com/cloudevents/spec/tree/v1.0.2

PostgreSQL Global Development Group. (2026). *CREATE POLICY*. In *PostgreSQL 16 documentation*. https://www.postgresql.org/docs/16/sql-createpolicy.html

PostgreSQL Global Development Group. (2026). *CREATE TRIGGER*. In *PostgreSQL 16 documentation*. https://www.postgresql.org/docs/16/sql-createtrigger.html

Temoshok, D., Choong, Y.-Y., Galluzzo, R., LaSalle, M., Regenscheid, A., Proud-Madruga, D., Gupta, S., & Lefkovitz, N. (2025). *Digital identity guidelines* (NIST Special Publication 800-63-4). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-63-4

Temoshok, D., Fenton, J., Choong, Y.-Y., Lefkovitz, N., Regenscheid, A., Galluzzo, R., & Richer, J. (2025). *Digital identity guidelines: Authentication and authenticator management* (NIST Special Publication 800-63B-4). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-63B-4

## Source verification date

Primary sources were rechecked on 2026-08-21. NIST identifies SP 800-63-4 and SP 800-63B-4 as final July 2025 publications; the CloudEvents repository identifies v1.0.2 as the latest released core specification; PostgreSQL URLs above are the official version-16 documentation.
