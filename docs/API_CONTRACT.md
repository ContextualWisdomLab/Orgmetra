# API Contract

## Versioning

Orgmetra APIs use OpenAPI 3.2.0. Major versions are path-scoped under `/v1` until a breaking contract requires `/v2`.

## Authentication

Every operation requires a Keyverse OpenID Connect bearer token. The gateway verifies issuer, audience, signature, expiration, subject, tenant binding, actor binding, and the operation-specific least-privilege scope before generated request validation reaches a domain handler.

The baseline scope contract is:

| Operation family | Required scope |
|---|---|
| People mutations | `orgmetra.people.write` |
| Confirmed-hire materialization | `orgmetra.people.materialize_worker` |
| Job-architecture mutations | `orgmetra.job_architecture.write` |
| Talent-acquisition mutations | `orgmetra.talent_acquisition.write` |

Scopes are coarse API capabilities. A caller-supplied business purpose remains a finer authorization input and cannot enlarge a token's scope or authorize itself.

## Command requirements

Every mutating request requires:

- exactly one validated `Idempotency-Key`;
- an authenticated actor whose token is bound to the target tenant;
- an explicit business purpose;
- resource-scoped authorization; and
- a command digest stored with the idempotency record.

Employment, position, assignment, person, job-profile, and selection-decision commands carry tenant, actor, and purpose through the reusable `X-Tenant-Reference`, `X-Actor-Reference`, and `X-Purpose-Code` components. The confirmed-hire route instead binds tenant in `/v1/tenants/{tenant_record_id}/candidate-worker-conversions`, purpose in the required query parameter, and actor through the authenticated principal; those path/query/authentication bindings are authoritative for that route and are not duplicated as weaker caller-controlled headers.

High-impact commands additionally require:

- decision reason;
- single-use human confirmation reference;
- at least one opaque evidence reference;
- an explicit evidence version for every reference; and
- append-only decision and audit records.

For confirmed-hire materialization, those high-impact facts are resolved from the exact already-sealed `selection_decision` and its evidence set inside the tenant-bound transaction rather than accepted again as mutable request-body assertions.

The server rejects a reused idempotency key when its method, resource, tenant, actor, purpose, or semantic command digest differs. People employment, position, assignment, and confirmed-hire writes persist that digest on `people_mutation_idempotency_record` in the same transaction as the authoritative HRIS fact and audit/outbox pair. A matching retry returns the first committed record identity without duplicating authoritative or audit/outbox facts. Generated record identifiers are excluded from the employment/position/assignment digest so a retried POST that allocates fresh UUIDs still replays; the confirmed-hire route requires the caller to repeat the exact confirmed identities and rejects a same-key command whose materialization identities differ.

## Organization hierarchy application

The active PR #119 database boundary is an internal `organization_core` mutation contract, not a public endpoint or a review-packet authorization. An authenticated Orgmetra command handler must pass the exact tenant and Organization Unit, expected predecessor version, successor identity, canonical review JSON and SHA-256 digest, distinct reviewer/applier correlations, and preallocated audit/outbox identities to `apply_organization_hierarchy_change(...)`. The function re-resolves current bitemporal truth and rejects stale evidence, missing or cross-unit version bindings, self-parenting, cycles at effective-time boundaries, and malformed review JSON. A serialization failure (`40001`) requires the caller to retry the complete command in a fresh transaction; no partial HRIS mutation is successful.

## Example endpoints

```text
POST /v1/person-records
GET  /v1/person-records/{person_record_id}
POST /v1/tenants/{tenant_record_id}/candidate-worker-conversions?purpose=candidate_hire
POST /v1/employment-records
POST /v1/position-records
POST /v1/assignment-records
POST /v1/job-profiles
POST /v1/job-profiles/{job_profile_id}/publish
POST /v1/candidate-profiles
POST /v1/selection-decisions
POST /v1/criterion-observations
POST /v1/validity-studies
```

The foundation OpenAPI contract covers the shared command vocabulary and baseline person, employment, position, assignment, job-profile, and selection-decision operations. Runtime services must publish any additional path-specific contract before release and may not weaken the shared `Idempotency-Key`, least-privilege scope, authorization, evidence, or error semantics. Employment and assignment writes fail closed when exclusive jobs overlap, a seat is not staffable, or visible seat allocations exceed 1.0000.

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
