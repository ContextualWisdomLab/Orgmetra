# Changelog

## Unreleased

- Add a purpose-bound audit evidence review request with a 90-day system-recorded window and 200-row maximum.
- Require authoritative exact-scope authorization before the audit-store reader is invoked.
- Re-verify persisted canonical JSON, SHA-256 digest, CloudEvents version/media type, tenant/event identity, review window, result count, and deterministic `(recorded_at, audit_event_record_id)` ordering before evidence is returned.
- Keep HR application values and employment-decision authority outside the review contract.
- Add exact statement and branch coverage over the installed wheel plus clean-checkout enforcement.
