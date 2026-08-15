# People API v1 contract

## Customer action before integration

Implement and review a `TokenAuthorizer` that validates the deployment's bearer
credentials, binds issuer and audience, resolves an opaque tenant and actor, and
returns only purposes explicitly granted to that actor. Do not expose the API to
production traffic with a static token or a caller-selected tenant header.

## Base behavior

- Media type: `application/json`
- Error media type: `application/problem+json`
- Authentication: HTTP Bearer through the injected authorizer
- Public identifiers: UUID values represented as strings
- Maximum request body: 65,536 bytes by default
- Unknown request fields: rejected
- Response caching: `Cache-Control: no-store`
- Request evidence: `X-Request-Id` response header

## Optional request metadata

| Header | Format | Meaning |
| --- | --- | --- |
| `X-Correlation-Id` | UUID | Existing workflow correlation; server trace is used when absent |
| `X-Decision-Reference` | UUID | Existing approved decision record, when applicable |
| `X-Evidence-Reference` | 1-512 printable characters | Opaque evidence locator; never raw evidence content |

These headers never select tenant or purpose. They are metadata after
authentication and authorization, not credentials.

## Purpose map

| Operation | Required server-selected purpose |
| --- | --- |
| Create person | `people_admin` |
| Read person | `people_read` |
| Create candidate | `talent_acquisition` |
| Link candidate to worker | `talent_acquisition` |
| Read audit evidence | `audit_review` |

## Endpoints

### `GET /health`

Process liveness only. A `200` response does not claim PostgreSQL or identity
provider readiness.

```json
{"status":"alive"}
```

### `POST /v1/people`

Creates one effective-dated person identity idempotently.

```json
{
  "person_record_id": "0198a412-6000-7000-8000-000000000010",
  "display_name": "Employee Name",
  "effective_from": "2026-08-15",
  "effective_to": null,
  "recorded_at": "2026-08-15T08:30:00Z"
}
```

The display name is authorized HR data, not audit metadata. Conflicting reuse of
an immutable person identifier returns `409` without revealing existing values.

### `GET /v1/people/{person_record_id}`

Returns the current recorded version visible to the authenticated tenant. An
absent and an unauthorized record both produce the same `404` response.

### `POST /v1/candidates`

Creates one candidate profile. `application_status_code` uses lower-case ASCII
letters, digits and underscores and is at most 64 characters.

### `POST /v1/candidates/{candidate_profile_id}/worker-links`

Appends the candidate-to-worker bridge after hire. Repeating the same identity is
idempotent; attempting to link the candidate to another worker returns `409`.

### `GET /v1/audit-events/{resource_record_id}`

Returns reference-only control evidence. It does not return names, resumes,
assessment responses, compensation values or document bodies.

## Problem details

The service uses RFC 9457-compatible documents for its explicit application
errors.

```json
{
  "type": "urn:orgmetra:problem:purpose_not_authorized",
  "title": "Purpose not authorized",
  "status": 403,
  "detail": "The authenticated principal is not authorized for this purpose.",
  "instance": "/v1/people",
  "error_code": "purpose_not_authorized",
  "trace_reference": "0198a412-6000-7000-8000-000000000003"
}
```

| Status | Stable error code | Next customer action |
| ---: | --- | --- |
| 400 | `invalid_request_metadata` | Correct UUID or evidence-reference headers |
| 401 | `authentication_failed` | Obtain a valid bearer credential |
| 403 | `purpose_not_authorized` | Request the correct role/purpose grant |
| 403 | `repository_access_denied` | Verify tenant and database-role policy |
| 404 | `resource_not_found` | Verify the opaque resource identifier and scope |
| 409 | `immutable_identity_conflict` | Reuse the original facts or create a new version/identity |
| 413 | `request_body_too_large` | Submit a smaller bounded document |
| 422 | `request_validation_failed` | Correct fields listed by path and issue code |
| 503 | `repository_unavailable` | Retry after the indicated interval |
| 500 | `internal_error` | Supply the trace reference to an authorized operator |

## Pre-GA exclusions

- production Keyverse OIDC/JWKS adapter and revocation;
- dependency readiness and degraded-state endpoint;
- tenant/user rate limits;
- signed idempotency-key ledger beyond identifier idempotency;
- framework-wide conversion of every unknown-route/method error to the same
  problem schema;
- deployment manifests, ingress controls and trusted proxy policy;
- OpenTelemetry, SLO evidence and incident runbooks;
- externally reviewed penetration and privacy assessment.
