# Employment-history HTTP read references

**Scope:** Standards basis for active PR #155. This file does not claim certification or protected-main integration.

## APA 7 references

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). RFC Editor. https://doi.org/10.17487/RFC3339

National Institute of Standards and Technology. (2020). *Zero trust architecture* (NIST Special Publication 800-207). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207

National Institute of Standards and Technology. (2023). *A zero trust architecture model for access control in cloud-native applications in multi-cloud environments* (NIST Special Publication 800-207A). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-207A

OpenAPI Initiative. (2025). *OpenAPI Specification v3.2.0*. https://spec.openapis.org/oas/v3.2.0

PostgreSQL Global Development Group. (2025). *PostgreSQL 18 documentation: Date/time types*. https://www.postgresql.org/docs/18/datatype-datetime.html

## Decision relevance

RFC 3339 constrains the customer-visible `known_at` representation to an
unambiguous UTC instant. OpenAPI defines the published operation, parameter,
response, and error-envelope contract. NIST zero-trust guidance informs
explicit identity/resource authorization at the HTTP boundary. PostgreSQL
date/time semantics support the repository's separation of business dates from
timezone-aware system-recorded instants; the service remains responsible for
the complete bitemporal contract.

These references constrain the transport adapter only. They do not authorize
scope expansion into compensation, performance, candidate, credential, or
automated employment-decision data.

## Review date

Rechecked as current primary references on 2026-08-30. Re-review if the
published OpenAPI major version, supported PostgreSQL major version, or cited
NIST authorization guidance changes.
