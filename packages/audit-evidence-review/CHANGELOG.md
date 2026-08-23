# Changelog

## Unreleased

- Add a purpose-bound audit evidence review request with a 90-day system-recorded window and 200-row maximum.
- Require authoritative exact-scope authorization before the audit-store reader is invoked.
- Add `PostgresAuditEvidenceRowReader` for the existing forced-RLS `public.audit_event_record`: it uses a read-only transaction, verifies the current PostgreSQL role is `NOSUPERUSER NOBYPASSRLS`, binds transaction-local tenant context, applies the authorized half-open recorded-time window and limit with parameterized SQL, and returns governed row snapshots only.
- Revalidate live query, authorization, and persisted-row fields into detached governed snapshots before authority/store use or evidence return, so post-construction `object.__setattr__` mutation cannot widen request bounds, forge permission, or bypass evidence checks.
- Re-verify persisted canonical JSON, SHA-256 digest, CloudEvents version/media type, tenant/event identity, review window, result count, and deterministic `(recorded_at, audit_event_record_id)` ordering before evidence is returned.
- Fail closed if stored canonical evidence is widened beyond the existing PII-minimized audit envelope/data key sets, even when a privileged rewrite recomputes a matching SHA-256 digest.
- Normalize unencodable canonical text to a stable validation failure before hashing or parsing.
- Keep HR application values, cross-service SQL, and employment-decision authority outside the review contract.
- Add exact statement and branch coverage over the installed wheel plus clean-checkout enforcement.
