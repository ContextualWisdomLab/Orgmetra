# Position history read references

**Scope:** Research and standards basis for active PR #152. This file does not claim certification or protected-main integration.

The Position-history contract uses established temporal/database and security-control concepts rather than creating Orgmetra-specific substitutes for them. Implementation details remain constrained by the actual protected-main schema and executable tests.

## APA 7 references

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 5.5. Constraints*. https://www.postgresql.org/docs/18/ddl-constraints.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 8.17. Range types*. https://www.postgresql.org/docs/18/rangetypes.html

## Decision relevance

### PostgreSQL range and exclusion semantics

The protected Orgmetra schema already uses database-level bitemporal constraints. PostgreSQL's range/exclusion facilities provide the primary technical basis for treating effective intervals as non-overlapping business truth where the schema requires it. The application read boundary does not replace those constraints; it independently rejects contradictory adapter output before buyer-visible serialization.

### RFC 3339 timestamps

System-recorded evidence is serialized in one UTC RFC 3339 representation (`Z`). This is an interoperability/canonicalization choice. The service separately validates that trust-bearing input is an exact built-in UTC datetime rather than accepting arbitrary caller-controlled timezone implementations that merely produce a zero offset.

### NIST SP 800-53 Rev. 5

The read boundary is designed toward evidence-ready access-control, least-privilege, auditability, and system/information-integrity practices. The design does not claim NIST compliance, SOC 2 certification, CSAP certification, or any external attestation. Purpose-bound authorization and field minimization are product controls whose effectiveness must remain demonstrable through exact-current executable evidence.

## Research classification

These references inform accepted architecture for PR #152. They do not authorize scope expansion into Person, Assignment, compensation, candidate, performance, or employment-decision data, and they do not supersede dedicated-writer dependency contracts.
