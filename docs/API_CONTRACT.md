# API Contract

## Versioning

Orgmetra APIs use OpenAPI 3.2.0. Major versions are path-scoped under `/v1` until a breaking contract requires `/v2`.

## Authentication

Every operation requires a Keyverse OpenID Connect bearer token. The gateway verifies issuer, audience, signature, expiration, subject, tenant binding, and actor binding before generated request validation reaches a domain handler.

## Command requirements

Every mutating request requires:

- `Idempotency-Key`;
- `X-Tenant-Reference`;
- `X-Actor-Reference`;
- `X-Purpose-Code`;
- an authenticated actor whose token is bound to the tenant;
- resource-scoped authorization; and
- a command digest stored with the idempotency record.

High-impact commands additionally require:

- decision reason;
- single-use human confirmation reference;
- at least one opaque evidence reference;
- an explicit evidence version for every reference; and
- append-only decision and audit records.

The server rejects a reused idempotency key when its method, resource, tenant, actor, purpose, or request digest differs.

## Example endpoints

```text
POST /v1/person-records
GET  /v1/person-records/{person_record_id}
POST /v1/employment-records
POST /v1/job-profiles
POST /v1/job-profiles/{job_profile_id}/publish
POST /v1/candidate-profiles
POST /v1/selection-decisions
POST /v1/candidate-worker-links
POST /v1/criterion-observations
POST /v1/validity-studies
```

The baseline OpenAPI contract includes representative person, job-profile, and selection-decision commands. Every additional mutation must reuse the same parameter components and high-risk schema composition rather than define weaker local fields.

## Error shape

```json
{
  "error_code": "evidence_required",
  "message": "This decision requires at least one versioned evidence reference.",
  "trace_id": "opaque_trace_reference",
  "details": {
    "missing_fields": ["evidence_references"]
  }
}
```
