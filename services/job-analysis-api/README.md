# Orgmetra Job-Analysis API

This service persists one immutable `JobAnalysisSnapshot` as tenant-scoped 3NF
rows and returns the same snapshot document on read. The kernel remains the
evidence contract. This boundary owns authorization, Idempotency-Key handling,
parent-scope fail-closed checks, and the transactional
`record_audit_outbox_event(...)` write.

The snapshot is occupational evidence about a Job, not a hiring, promotion,
termination, compensation, or other high-impact employment decision. Purpose-bound
authorization is required; job-analysis fields are not blanket-masked as PII.

Supported routes:

- `POST /v1/tenants/{tenant_record_id}/job-analysis-snapshots`
- `GET /v1/tenants/{tenant_record_id}/job-analysis-snapshots/{analysis_record_id}`

The tenant authority comes from the path and must match the authenticated
principal's tenant. The actor authority comes from the authenticated principal;
these routes do not accept duplicate caller-controlled tenant or actor headers.
POST requires `Authorization`, `Content-Type: application/json`,
`Idempotency-Key`, and `X-Purpose-Code`. Missing, non-ASCII, or non-JSON media
types receive `415 unsupported_media_type` before the body is read. Optional
`position_record_id` and `criterion_blueprint_id` may be included and are bound
through foreign keys that fail closed when the parent is missing. GET requires
`Authorization` and `X-Purpose-Code`, accepts no query parameters, and returns
the persisted snapshot document.

Attacker-controlled request metadata is bounded before bearer authentication.
The transport rejects paths longer than 256 characters before splitting route
segments or parsing UUIDs, accepts at most 64 ASGI header frames, and accepts at
most 16 KiB of aggregate header-name and header-value bytes before lower-casing
or dictionary allocation. Requests above a header budget fail closed as
authentication failures, while an oversized path fails route recognition; none
reaches the identity provider, authorization policy, request body, or persistence
boundary.

Posted evidence is bounded and unambiguous. The transport stops reading once the
cumulative chunked body exceeds 1 MiB and rejects duplicate JSON member names at
any object depth. The snapshot parser enforces exact top-level, Task, KSAO,
Task–KSAO link, FJA, and provenance-source field allowlists. Unsupported fields
are rejected rather than silently discarded or collapsed into the digest of a
different accepted command.

Every customer-facing error includes the stable `error_code`, explanatory
`message`, actionable `next_action`, and a random `support_reference` that does
not encode tenant, trace, topology, timestamp, credential, or PII. The legacy
`error` field is retained only as a deprecated alias for `error_code` while
clients migrate; new integrations must use `error_code`.
