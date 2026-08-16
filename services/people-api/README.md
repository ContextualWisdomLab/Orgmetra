# orgmetra-people-api

`orgmetra-people-api` is a small FastAPI application factory for the first
Orgmetra people and talent vertical slice. It converts authenticated,
purpose-authorized HTTP requests into `orgmetra-postgres` repository operations
without accepting tenant identity from an untrusted header.

## Implemented endpoints

- `GET /health`
- `POST /v1/people`
- `GET /v1/people/{person_record_id}`
- `POST /v1/employment-records`
- `GET /v1/employment-records/{employment_record_id}`
- `POST /v1/candidates`
- `GET /v1/candidates/{candidate_profile_id}`
- `POST /v1/candidates/{candidate_profile_id}/worker-links`
- `GET /v1/candidates/{candidate_profile_id}/worker-links`
- `GET /v1/audit-events/{resource_record_id}`

## Trust boundary

The host supplies a `TokenAuthorizer` implementation. The authorizer validates
the bearer token and returns opaque tenant and actor references only after the
required route scope and purpose are both authorized. Route handlers construct
the immutable `PurposeContext` through runtime FastAPI dependencies; clients
cannot choose a tenant, purpose, repository, or request object with query
fields or arbitrary headers.

The package has no default production authorizer, no static-token fallback and
no environment-variable composition. A deployment must compose an approved
identity adapter, such as a future Keyverse OIDC integration, and a
`PostgresPeopleRepository` explicitly.

## HTTP behavior

- RFC 9457-compatible `application/problem+json` errors
- opaque request/correlation identifiers
- bounded JSON request bodies
- `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and
  `Referrer-Policy: no-referrer`
- no permissive CORS default
- no SQL, credentials, PII, or exception text in client errors

This is a pre-GA application boundary. Production OIDC/JWKS validation,
revocation, rate limiting, ingress body limits, deployment manifests, readiness
checks, OpenTelemetry and external penetration testing remain release gates.
