# Unreleased: purpose-bound People API

## Added

- dependency-injected FastAPI application factory
- server-selected people, talent-acquisition and audit purposes
- strict people, candidate, worker-link and audit schemas
- bounded request-body middleware with opaque request evidence
- RFC 9457-compatible application problem responses
- stable OpenAPI operation identifiers and bearer security scheme
- Python 3.12/3.14 exact coverage and docstring quality gates

## Security

- tenant identity comes only from an injected authorizer
- no static production token, raw tenant header, permissive CORS or ambient
  environment composition
- validation and repository failures do not echo tokens, SQL or HR content
- synchronous repository calls leave the event loop through the threadpool
- CI uses minimal permissions, immutable action revisions and no model secrets

## Known limits

Production Keyverse OIDC/JWKS validation, readiness, rate limiting, trusted proxy
policy, full framework error normalization, deployment manifests,
OpenTelemetry/SLO evidence, dependency hashes/attestations and external security
review remain release gates.
