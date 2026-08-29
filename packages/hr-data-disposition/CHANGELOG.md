# Changelog

## Unreleased

- Add `HrDataDispositionExecutionRequest` as a value-minimized, human-review-required request artifact that never grants execution authority.
- Bind exact tenant/resource, upstream retention-review digest, retention-policy digest, post-due chronology, clear legal-hold state, closed disposition action, distinct requester/reviewer actors, evidence version, and exact UTC system time.
- Reject caller-defined scalar subclasses, malformed/noncanonical references, stale upstream retention states, active holds, due-date/non-post-due requests, same-actor review, and post-construction evidence mutation, including independently valid replacement after creation.
- Reject future values for the system-recorded timestamp so chronology cannot be forged.
- Make the trust-bearing request runtime-final so callers cannot override derived execution-authorization or sanitization states through inheritance.
- Keep execution explicitly `not_authorized_to_execute`, require authoritative re-resolution before any executor acts, and emit `media_sanitization_state=not_claimed` so application disposition cannot be mistaken for storage-media sanitization.
- Require deterministic canonical JSON/SHA-256 evidence and exact 100% owned production statement/branch coverage.
- Seal creation-time request evidence outside packet-writable state so a forged in-object digest cannot authorize a rewritten canonical request.
