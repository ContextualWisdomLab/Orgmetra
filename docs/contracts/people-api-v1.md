# People API v1 contract

## Status

This contract describes behavior implemented on the active People API PR. It is
not protected default-branch or release truth until the dependency stack merges
and the retargeted exact head passes fresh integrated checks and applicable review.

## Customer action before integration

Inject a reviewed `TokenAuthorizer` that validates bearer credentials, binds
issuer and audience, resolves opaque tenant and actor references, and returns
independently granted operation scopes and HR purposes. Do not expose the API to
production traffic with a static token or caller-selected tenant, actor, scope,
purpose, decision, or evidence authority.

## Base behavior

- Media type: `application/json`
- Error media type: `application/problem+json`
- Authentication: HTTP Bearer through the injected authorizer
- Authorization: route-owned operation scope plus route-owned business purpose
- Server-owned dependencies: `PurposeContext` and the repository port are
  injected at runtime; they are not OpenAPI query, path, or header fields
- Public record identifiers: UUID strings
- Maximum request body: 65,536 bytes by default
- Unknown request fields: rejected
- Response caching: `Cache-Control: no-store`
- Client support evidence: random `X-Support-Reference` matching `err_[A-Za-z0-9_-]{20,80}`
- Internal trace identifiers are not returned to clients

## Optional request metadata

| Header | Format | Meaning |
| --- | --- | --- |
| `X-Correlation-Id` | UUID | Existing workflow correlation; internal trace correlation is used when absent |

Caller-provided decision and evidence headers are deliberately not accepted as
audit provenance. Governed decision/evidence references must be resolved by an
authorized application workflow and persisted through a versioned evidence
contract before a high-impact decision surface can rely on them.

## Scope and purpose map

| Operation | Required operation scope | Required business purpose |
| --- | --- | --- |
| Create person | `orgmetra.people.write` | `people_admin` |
| Read person | `orgmetra.people.read` | `people_read` |
| Create candidate | `orgmetra.talent_acquisition.write` | `talent_acquisition` |
| Link candidate to worker | `orgmetra.talent_acquisition.write` | `talent_acquisition` |
| Read audit evidence | `orgmetra.audit.read` | `audit_review` |

Both dimensions must be present. A valid purpose cannot substitute for a missing
operation scope, and a valid scope cannot substitute for a missing purpose.

## Endpoints

### `GET /health`

Process liveness only. A `200` response does not claim PostgreSQL or identity
provider readiness.

```json
{"status":"alive"}
```

### `POST /v1/people`

Creates one effective-dated person identity. The request may specify business
time but cannot specify system-recorded time.

```json
{
  "person_record_id": "0198a412-6000-7000-8000-000000000010",
  "display_name": "Employee Name",
  "effective_from": "2026-08-15",
  "effective_to": null
}
```

PostgreSQL owns `recorded_from`. Conflicting reuse of an immutable person
identifier returns `409` without revealing existing values.

### `GET /v1/people/{person_record_id}`

Returns the current recorded version visible to the authenticated tenant. An
absent and an unauthorized record produce the same `404` response.

### `POST /v1/candidates`

Creates one candidate profile. `application_status_code` uses lower-case ASCII
letters, digits and underscores and is at most 64 characters.

### `POST /v1/candidates/{candidate_profile_id}/worker-links`

Appends the candidate-to-worker bridge after hire. The current endpoint has only
identity-level idempotency and therefore remains pre-GA until the shared
idempotency ledger and governed human-confirmation/evidence contract are wired
through persistence atomically.

### `GET /v1/audit-events/{resource_record_id}`

Returns reference-only control evidence. It does not return names, resumes,
assessment responses, compensation values or document bodies.

## Problem details

Explicit application errors use RFC 9457-compatible documents with actionable
next steps and a client-safe random support identifier.

```json
{
  "type": "urn:orgmetra:problem:authorization_denied",
  "title": "Authorization denied",
  "status": 403,
  "detail": "The authenticated principal is not authorized for this operation.",
  "instance": "/v1/people",
  "error_code": "authorization_denied",
  "support_reference": "err_7M2mY0M_yiRU3Q-BRrRcqLEioVcUBEVB",
  "next_action": "Request the required operation scope and business-purpose grant before retrying."
}
```

| Status | Stable error code | Next customer action |
| ---: | --- | --- |
| 400 | `invalid_request_metadata` | Correct bounded correlation metadata |
| 401 | `authentication_failed` | Obtain a valid bearer credential |
| 403 | `authorization_denied` | Request both required scope and purpose grants |
| 403 | `repository_access_denied` | Verify tenant and database-role policy |
| 404 | `resource_not_found` | Verify the opaque resource identifier and scope |
| 409 | `immutable_identity_conflict` | Reuse the original facts or create a governed new version |
| 413 | `request_body_too_large` | Submit a smaller bounded document |
| 422 | `request_validation_failed` | Correct fields listed by path and issue code |
| 503 | `repository_unavailable` | Retry after the indicated interval |
| 500 | `internal_error` | Supply the support reference to an authorized operator |

## Remaining pre-GA gates

- production Keyverse OIDC/JWKS adapter, revocation, issuer/audience/algorithm and key-rotation policy;
- atomic idempotency-key ledger binding actor, tenant, purpose, resource, operation and command digest;
- governed human confirmation, reason and versioned evidence for high-impact mutations;
- dependency readiness/degraded-state endpoint and tenant/user rate limits;
- deployment manifests, ingress controls and trusted proxy policy;
- privacy-safe OpenTelemetry, SLO evidence and incident runbooks;
- SBOM, artifact provenance and externally reviewed penetration/privacy assessment.
