# Position-history HTTP read references

**Scope:** Standards basis for active PR #154. This file does not claim certification or protected-main integration.

## APA 7 references

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

OpenAPI Initiative. (2025). *OpenAPI Specification v3.2.0*. https://spec.openapis.org/oas/v3.2.0

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Row security policies*. https://www.postgresql.org/docs/18/ddl-rowsecurity.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: SET TRANSACTION*. https://www.postgresql.org/docs/18/sql-set-transaction.html

## Decision relevance

RFC 3339 constrains the customer-visible `known_at` representation to an
unambiguous UTC instant. OpenAPI defines the published operation, parameter,
response, and error-envelope contract. PostgreSQL row security and read-only
transaction controls remain persistence defense in depth; the application still
binds the tenant, purpose, exact target, requested fields, and service policy
before serialization. NIST access-control and information-integrity guidance
informs least privilege and fail-closed error handling without implying a
compliance outcome.

## Research classification

These references constrain the HTTP adapter architecture for PR #154. They do
not authorize scope expansion into Person, Employment, Assignment, compensation,
candidate, performance, credential, or automated employment-decision data.
