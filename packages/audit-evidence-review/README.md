# Orgmetra Audit Evidence Review

This package is the purpose-bound review boundary for Orgmetra's existing immutable `audit_event_record` evidence. It makes one ordering guarantee explicit: **authorization happens before any audit-store read**. It then re-verifies the exact persisted canonical JSON, SHA-256 digest, tenant/event binding, system-recorded review window, row bound, and deterministic row order before returning evidence to an authorized reviewer.

## What it does

`AuditEvidenceQuery` carries only tenant scope, an opaque review correlation, a pseudonymous requester correlation, the closed purpose `audit_evidence_review`, a bounded system-recorded interval, and a maximum result count. The interval is capped at 90 days and a page at 200 rows.

`AuditEvidenceReadAuthority` is a host-owned protocol. A production host must resolve the authenticated actor and purpose through the authoritative policy/identity boundary and return an exact-scope `AuditEvidenceReadAuthorization`. Constructing that dataclass does **not** itself prove authorization.

`AuditEvidenceRowReader` is a read-only adapter protocol for the existing Orgmetra audit store. A production PostgreSQL adapter must use a least-privileged `NOSUPERUSER NOBYPASSRLS` application role, `SET TRANSACTION READ ONLY`, bind `orgmetra.tenant_record_id`, rely on the existing forced-RLS `audit_event_record` relation, constrain `recorded_at` to the authorized half-open interval, order by `(recorded_at, audit_event_record_id)`, and apply the authorized limit. This package deliberately does not duplicate persistence SQL or cross-service application tables.

`PersistedAuditEvidenceRow` performs defense-in-depth verification after the read: exact canonical bytes must match the lower-case SHA-256 digest; the bytes must round-trip through Orgmetra's deterministic JSON form; CloudEvents `specversion`/media type must match the governed envelope; and the event id and tenant in canonical evidence must match the persisted row columns.

## Privacy and decision boundary

The review result exposes only the canonical audit envelope already designed to be PII-minimized. It does not read Person names, contact details, compensation, ratings, candidate content, free-form feedback, credentials, or model output from application tables. Opaque actor/resource references remain correlation data and still require purpose-bound access control, retention, export control, and audit handling.

This package grants **no** employment-decision authority and makes no decision. It does not make LLM output authoritative. High-impact employment decisions remain subject to their separate human-confirmation boundaries and immutable evidence contracts.

## Failure behavior

The boundary fails closed before returning evidence when authorization is absent, denied, malformed, or scope-mismatched; when the reader returns a mutable/non-tuple collection, too many rows, a non-governed row, cross-tenant evidence, out-of-window evidence, non-monotonic row order, noncanonical JSON, or a digest/identity mismatch.

A storage adapter failure propagates to the host; callers must not reinterpret missing evidence as an empty successful review.

## Current status

This package is **active-PR evidence**, not protected-main shipped truth until its pull request is integrated. The production PostgreSQL reader and customer-facing audit UI are follow-on host adapters and must preserve this contract rather than weakening it.
