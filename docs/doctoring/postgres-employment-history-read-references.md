# PostgreSQL Employment-history read references

**Scope:** Standards and research basis for active PR #156. This file does not claim certification or protected-main integration.

## APA 7 references

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://doi.org/10.1109/69.755613

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Range types*. https://www.postgresql.org/docs/current/rangetypes.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies*. https://www.postgresql.org/docs/current/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: SET TRANSACTION*. https://www.postgresql.org/docs/current/sql-set-transaction.html

Snodgrass, R. T. (1999). *Developing time-oriented database applications in SQL*. Morgan Kaufmann. https://lccn.loc.gov/99014298

## Decision relevance

PostgreSQL transaction access mode and isolation support the adapter's explicit `READ COMMITTED, READ ONLY` boundary. Row security remains database defense in depth, while the application binds tenant context and checks exact returned identity. Range and exclusion semantics remain the schema-level basis for bitemporal non-overlap; this read adapter does not replace those constraints.

RFC 3339 supports one interoperable UTC representation for system-recorded evidence. Jensen and Snodgrass and Snodgrass support keeping effective/business time distinct from transaction/system time. NIST SP 800-53 Rev. 5 informs least privilege and information-integrity evidence readiness; no compliance or certification claim follows from this PR.

## Research classification

These references constrain the accepted adapter architecture for PR #156. They do not authorize scope expansion into compensation, candidate, performance, credentials, or employment-decision automation.
