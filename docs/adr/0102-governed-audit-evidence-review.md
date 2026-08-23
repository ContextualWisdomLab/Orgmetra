# ADR 0102: Governed audit evidence review boundary

Status: Proposed

## Context

Protected `develop` already persists a PII-minimized CloudEvents-compatible canonical audit envelope and SHA-256 digest in `audit_event_record` under forced tenant RLS. The repository did not yet define an executable read-side trust boundary for audit review. A caller could otherwise implement ad hoc reads that fetch evidence before authorization, fail to bind authorization to the exact tenant/request/purpose, return unbounded history, or trust persisted bytes without rechecking their digest and row identity.

NIST SP 800-53 Rev. 5.1 AU-6 calls for review and analysis of system audit records, while CloudEvents v1.0.2 defines the stable event context contract used by Orgmetra's existing audit envelope. These sources motivate reviewability and interoperability; they do not make this package a certification or a complete security-monitoring system.

## Decision

Introduce an Orgmetra-owned, transport-neutral `audit-evidence-review` package with four explicit boundaries:

1. `AuditEvidenceQuery` fixes tenant scope, pseudonymous request/requester correlations, the closed `audit_evidence_review` purpose, a maximum 90-day system-recorded interval, and a maximum 200-row page.
2. `AuditEvidenceReadAuthority` must be invoked before any audit-store read. Its authorization result must exactly match tenant, query reference, requester and purpose and must explicitly permit the read.
3. `AuditEvidenceRowReader` remains a host adapter. PostgreSQL implementations must use the existing Orgmetra audit table and forced-RLS tenant context rather than cross-service SQL or a duplicate audit store.
4. Every returned `PersistedAuditEvidenceRow` re-verifies exact canonical JSON, SHA-256, CloudEvents version/media type, persisted tenant/event identity, authorized time window, result count and deterministic ordering before evidence reaches the reviewer.

The package returns the already PII-minimized canonical audit envelope and does not query application-table HR values. It does not grant or imply employment-decision authority. An empty page means the authorized bounded reader returned no rows; an adapter failure must remain a failure rather than being converted to an empty page.

## Consequences

The buyer gains an executable, testable control boundary for audit review without turning audit evidence into a shadow HR system of record. Host adapters retain responsibility for identity/policy resolution, PostgreSQL role selection, RLS context, query parameterization, observability and auditing the review itself. A customer-facing audit UI and concrete PostgreSQL reader may be added later only if they preserve authorization-before-read and exact evidence verification.

## Alternatives rejected

- **Expose `canonical_event_json` directly from arbitrary SQL.** Rejected because authorization ordering, bounds and integrity verification would be host-specific and easy to omit.
- **Copy HR fields into an audit-search index.** Rejected because it creates a second sensitive system of record and weakens minimization/retention boundaries.
- **Treat a successful database read as proof of evidence integrity.** Rejected because read-time digest and row-identity verification provides defense in depth against corruption or privileged storage tampering.
