# PostgreSQL Position-history read references

**Scope:** Standards and research basis for active PR #153. This file does not claim certification or protected-main integration.

## APA 7 references

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: SET TRANSACTION*. https://www.postgresql.org/docs/18/sql-set-transaction.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Range types*. https://www.postgresql.org/docs/18/rangetypes.html

## Decision relevance

PostgreSQL's transaction access mode and isolation level support the adapter's explicit `READ COMMITTED, READ ONLY` boundary. Row security remains database defense in depth, while the application still binds tenant context and checks exact returned identity. PostgreSQL range/exclusion semantics remain the schema-level basis for bitemporal non-overlap; this read adapter does not replace those constraints.

RFC 3339 and explicit UTC projection support one interoperable representation for system-recorded evidence. NIST SP 800-53 Rev. 5 informs least privilege, access control, and information-integrity evidence readiness; no compliance or certification claim follows from this PR.

## Research classification

These references constrain the accepted adapter architecture for PR #153. They do not authorize scope expansion into worker data, Assignment joins, compensation, candidate, performance, or employment-decision automation.
