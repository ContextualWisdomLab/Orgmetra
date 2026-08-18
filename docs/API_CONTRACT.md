# API Contract

## Versioning

Orgmetra APIs use OpenAPI 3.2.0. Major versions are path-scoped under `/v1` until a breaking contract requires `/v2`.

## Authentication

Every operation requires a Keyverse OpenID Connect bearer token. The gateway verifies issuer, audience, signature, expiration, subject, tenant binding, actor binding, and the operation-specific least-privilege scope before generated request validation reaches a domain handler.

The baseline scope contract is:

| Operation family | Required scope |
|---|---|
| People mutations | `orgmetra.people.write` |
| Job-architecture mutations | `orgmetra.job_architecture.write` |
| Talent-acquisition mutations | `orgmetra.talent_acquisition.write` |

Scopes are coarse API capabilities. `X-Purpose-Code` remains the finer business-purpose input and cannot enlarge a token's scope or authorize itself.

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

The server rejects a reused idempotency key when its method, resource, tenant, actor, purpose, or request digest differs. People employment, position, and assignment writes persist that digest on `people_mutation_idempotency_record` in the same transaction as the HRIS fact and audit/outbox pair. A matching retry returns the first committed record identity. Generated record identifiers are excluded from the digest so a retried POST that allocates fresh UUIDs still replays.

## Example endpoints

```text
POST /v1/person-records
GET  /v1/person-records/{person_record_id}
POST /v1/employment-records
POST /v1/position-records
POST /v1/assignment-records
POST /v1/job-profiles
POST /v1/job-profiles/{job_profile_id}/publish
POST /v1/candidate-profiles
POST /v1/selection-decisions
POST /v1/candidate-worker-links
POST /v1/criterion-observations
POST /v1/validity-studies
```

The baseline OpenAPI contract includes person, employment, position, assignment, job-profile, and selection-decision commands. Every additional mutation must reuse the same parameter components and high-risk schema composition rather than define weaker local fields. Employment and assignment writes fail closed when exclusive jobs overlap, a seat is not staffable, or visible seat allocations exceed 1.0000.

## Error shape

```json
{
  "error_code": "evidence_required",
  "message": "This decision requires at least one versioned evidence reference.",
  "next_action": "Attach an approved evidence version and retry with a new idempotency key.",
  "support_reference": "err_N7fx9z2TkQm4Wa8cR1pL6v"
}
```

`support_reference` is a randomly generated client-safe lookup key. It maps to restricted internal telemetry but never encodes or exposes an internal trace/span identifier, topology, timestamp, tenant identifier, credential, or PII.
