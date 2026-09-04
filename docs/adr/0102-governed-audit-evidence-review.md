# ADR 0102: Governed audit evidence review boundary

Status: Proposed

## Context

Protected `develop` already persists a PII-minimized CloudEvents-compatible canonical audit envelope and SHA-256 digest in `audit_event_record` under forced tenant RLS. The repository did not yet define an executable read-side trust boundary for audit review. A caller could otherwise implement ad hoc reads that fetch evidence before authorization, fail to bind authorization to the exact tenant/request/purpose, return unbounded history, or trust persisted bytes without rechecking their digest, row identity, and PII-minimized envelope shape.

NIST SP 800-53 Rev. 5 AU-6 calls for review and analysis of system audit records; the current NIST control catalog update reviewed for this decision is 5.2.0. CloudEvents v1.0.2 defines the stable event context contract used by Orgmetra's existing audit envelope. These sources motivate reviewability and interoperability; they do not make this package a certification or a complete security-monitoring system.

## Decision

Introduce an Orgmetra-owned, transport-neutral `audit-evidence-review` package with four explicit boundaries:

1. `AuditEvidenceQuery` fixes tenant scope, pseudonymous request/requester correlations, the closed `audit_evidence_review` purpose, a maximum 90-day system-recorded interval, and a maximum 200-row page.
2. `AuditEvidenceReadAuthority` must be invoked before any audit-store read. Its authorization result must exactly match tenant, query reference, requester and purpose and must explicitly permit the read.
3. `AuditEvidenceRowReader` is the read-only storage protocol. The included `PostgresAuditEvidenceRowReader` reads only the existing Orgmetra `public.audit_event_record` relation. It enters a read-only transaction, proves `CURRENT_USER` is neither `SUPERUSER` nor `BYPASSRLS`, sets transaction-local `orgmetra.tenant_record_id`, and executes a static parameterized query over the authorized half-open system-recorded interval with deterministic ordering and the authorized limit. Deployment composition owns TLS, credentials, pooling and the least-privileged login role.
4. Every returned `PersistedAuditEvidenceRow` re-verifies valid bounded UTF-8, standard finite JSON values, exact canonical JSON bytes, SHA-256, the protected-main PII-minimized top-level/nested envelope key sets and value types, CloudEvents version/media type, persisted tenant/event identity, authorized time window, result count and deterministic ordering before evidence reaches the reviewer.

The package returns the already PII-minimized canonical audit envelope and does not query application-table HR values or another service database. A privileged storage rewrite cannot make extra top-level HR fields or nested rating-like fields acceptable merely by recomputing a matching digest. The package does not grant or imply employment-decision authority. An empty page means the authorized bounded reader returned no rows; an adapter failure must remain a failure rather than being converted to an empty page.

## Consequences

The buyer gains an executable, testable control boundary for audit review without turning audit evidence into a shadow HR system of record. The PostgreSQL adapter makes least-privilege role state, tenant RLS binding, read-only transaction semantics, bounded parameterized SQL and stable ordering executable rather than leaving them only as host documentation. Host composition still retains responsibility for identity/policy resolution, credentials/TLS/pooling, observability and auditing the review itself. A customer-facing audit UI/API may be added later only if it preserves authorization-before-read and exact evidence verification.

## Alternatives rejected

- **Expose `canonical_event_json` directly from arbitrary SQL.** Rejected because authorization ordering, bounds and integrity verification would be host-specific and easy to omit.
- **Let a privileged or RLS-bypass database role perform audit review.** Rejected because it would make tenant isolation depend on application predicates alone rather than the existing forced-RLS defense in depth.
- **Copy HR fields into an audit-search index.** Rejected because it creates a second sensitive system of record and weakens minimization/retention boundaries.
- **Treat a successful database read as proof of evidence integrity.** Rejected because read-time digest, exact-envelope-shape and row-identity verification provide defense in depth against corruption or privileged storage tampering.
