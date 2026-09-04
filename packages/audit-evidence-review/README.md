# Orgmetra Audit Evidence Review

This package is the purpose-bound review boundary for Orgmetra's existing immutable `audit_event_record` evidence. It makes one ordering guarantee explicit: **authorization happens before any audit-store read**. It then re-validates the live query and authorization objects, re-verifies persisted evidence into detached row snapshots, and only then returns evidence to an authorized reviewer.

## What it does

`AuditEvidenceQuery` carries only tenant scope, an opaque review correlation, a pseudonymous requester correlation, the closed purpose `audit_evidence_review`, a bounded system-recorded interval, and a maximum result count. The interval is capped at 90 days and a page at 200 rows. `read_audit_evidence()` reconstructs the live query through this governed constructor before calling either authority or storage, so a once-valid frozen dataclass cannot be widened later with `object.__setattr__`.

`AuditEvidenceReadAuthority` is a host-owned protocol. A production host must resolve the authenticated actor and purpose through the authoritative policy/identity boundary and return an exact-scope `AuditEvidenceReadAuthorization`. Constructing that dataclass does **not** itself prove authorization. The returned object is also reconstructed through its governed constructor before permission or scope is trusted.

`AuditEvidenceRowReader` is the read-only storage protocol. `PostgresAuditEvidenceRowReader` is the included Orgmetra PostgreSQL implementation for the existing audit store. It opens `SET TRANSACTION READ ONLY`, proves the current login is neither `SUPERUSER` nor `BYPASSRLS`, binds the exact `orgmetra.tenant_record_id` transaction-local setting, reads only `public.audit_event_record`, constrains `recorded_at` to the authorized half-open interval, orders by `(recorded_at, audit_event_record_id)`, and applies the authorized limit through bound parameters. Deployment composition still owns connection pooling, TLS, credentials, and selection of the least-privileged application role. The adapter does not query HR application tables or any other service database.

`PersistedAuditEvidenceRow` performs defense-in-depth verification after the read: the canonical text must be valid UTF-8 within the byte budget; exact bytes must match the lower-case SHA-256 digest; those bytes must round-trip through Orgmetra's deterministic JSON form; the top-level and nested `data` keys must still match the existing PII-minimized audit envelope (with only the governed optional confirmation extension); CloudEvents `specversion`/media type must match the governed envelope; and event id and tenant in canonical evidence must match the persisted row columns. `read_audit_evidence()` reconstructs each live reader row and returns the reconstructed snapshot rather than the reader-owned object, so a row that was valid only at construction time cannot bypass current checks. A privileged rewrite cannot widen the envelope with extra HR fields merely by recomputing a matching digest.

## Privacy and decision boundary

The review result exposes only the canonical audit envelope already designed to be PII-minimized. It does not read Person names, contact details, compensation, ratings, candidate content, free-form feedback, credentials, or model output from application tables. Opaque actor/resource references remain correlation data and still require purpose-bound access control, retention, export control, and audit handling.

This package grants **no** employment-decision authority and makes no decision. It does not make LLM output authoritative. High-impact employment decisions remain subject to their separate human-confirmation boundaries and immutable evidence contracts.

## Failure behavior

The boundary fails closed before returning evidence when authorization is absent, denied, malformed, scope-mismatched, or post-construction-mutated; when the reader returns a mutable/non-tuple collection, too many rows, a non-governed or post-construction-mutated row, cross-tenant evidence, out-of-window evidence, non-monotonic row order, invalid/unencodable or noncanonical JSON, a widened envelope/data shape, or a digest/identity mismatch. The PostgreSQL adapter additionally fails closed before tenant context or evidence access when the current database role is a superuser or has `BYPASSRLS`, and it revalidates a directly supplied query before opening a connection.

A storage adapter failure propagates to the host; callers must not reinterpret missing evidence as an empty successful review.

## Current status

This package, including `PostgresAuditEvidenceRowReader`, is **active-PR evidence**, not protected-main shipped truth until its pull request is integrated. A customer-facing audit UI/API remains a follow-on host surface and must preserve authorization-before-read, tenant RLS, bounded evidence review, and exact evidence verification.
