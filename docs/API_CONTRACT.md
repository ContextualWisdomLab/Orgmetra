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

The server rejects a reused idempotency key when its method, resource, tenant, actor, purpose, or semantic command digest differs. People employment, position, assignment, confirmed-hire, and Employment-separation writes persist the corresponding digest in the same transaction as the authoritative HRIS fact and audit/outbox pair. A matching retry returns the first committed result without duplicating authoritative or audit/outbox facts. Generated record identifiers are excluded from the employment/position/assignment digest so a retried POST that allocates fresh UUIDs still replays; the confirmed-hire route requires the caller to repeat the exact confirmed identities and rejects a same-key command whose materialization identities differ. Employment separation binds the key to the exact tenant, Person, Employment, expected Employment version, effective separation date, controlled reason, actor, `workforce_admin` purpose, evidence version, and human confirmation; a semantic mismatch under the same key fails closed.

## Governed Employment separation

The active People contract on PR #64 introduces `POST /v1/employment-separations`. It is a high-impact governed lifecycle command, not an in-place status update. The command targets one exact current-known `active` or `leave` Employment version, requires human confirmation and versioned evidence, and produces bitemporal supersession plus immutable separation/audit/outbox/idempotency evidence in one PostgreSQL transaction.

`separation_reason_code` is a controlled Ubiquitous-Language value. The public contract accepts exactly:

- `voluntary_resignation`
- `retirement_transition`
- `fixed_term_completion`
- `position_elimination`
- `employer_initiated_separation`

Arbitrary lower-`snake_case` text is not a valid reason. The route also fails closed for stale expected versions, tenant or Person/Employment mismatches, incompatible future Employment truth, or Assignment truth that would remain effective on or after the requested separation boundary.

The continuation version's `effective_to` is only the structural end of the pre-separation interval. The terminal `employment_record_version` with status `terminated`, together with its `employment_separation_record`, is the authoritative separation fact. Rehire is not part of this route and remains planned under #302; it must not reopen a terminated Employment or treat an old candidate-worker conversion as rehire authority.

This route is active-PR truth, not protected/released truth, until #64 is normally integrated and ADR 0015's PostgreSQL/security/review acceptance conditions are satisfied. Consumers must not treat the active branch as an immutable external dependency.

## Example endpoints

```text
POST /v1/person-records
GET  /v1/person-records/{person_record_id}
POST /v1/tenants/{tenant_record_id}/candidate-worker-conversions?purpose=candidate_hire
POST /v1/employment-records
POST /v1/employment-separations
POST /v1/position-records
POST /v1/assignment-records
POST /v1/job-profiles
POST /v1/job-profiles/{job_profile_id}/publish
POST /v1/candidate-profiles
POST /v1/selection-decisions
POST /v1/criterion-observations
POST /v1/validity-studies
```

The foundation OpenAPI contract covers the shared command vocabulary and baseline person, employment, Employment-separation, position, assignment, job-profile, and selection-decision operations on the active #64 branch. Runtime services must publish any additional path-specific contract before release and may not weaken the shared `Idempotency-Key`, least-privilege scope, authorization, evidence, or error semantics. Employment and assignment writes fail closed when exclusive jobs overlap, a seat is not staffable, or visible seat allocations exceed 1.0000. Employment separation additionally serializes with Assignment creation on the same Employment aggregate conflict boundary.

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
