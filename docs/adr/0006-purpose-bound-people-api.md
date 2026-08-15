# ADR-0006: Dependency-injected purpose-bound People API

- Status: Proposed
- Date: 2026-08-15
- Owners: Orgmetra maintainers
- Depends on: ADR-0005
- Supersedes: none

## Context

The first durable Orgmetra repository requires a customer-facing application
boundary. A naive API that accepts `tenant_id` or `purpose` from request headers
would turn untrusted caller input into database authority. A default static token
or permissive development bypass could also be exposed accidentally. Blocking
synchronous database calls on the event loop would harm service isolation.

## Decision

Orgmetra will provide an independently importable FastAPI application factory
with the following contracts:

1. the host must inject a `TokenAuthorizer` and `PeopleRepository`;
2. there is no default production authorizer, static token, environment-driven
   bypass or permissive CORS configuration;
3. each route selects its required purpose in server code;
4. the authorizer returns opaque tenant and actor references after token and
   purpose authorization;
5. the route constructs `PurposeContext`; no tenant or purpose header exists;
6. synchronous repository calls execute through Starlette's bounded threadpool;
7. request bodies are bounded by declared and observed bytes;
8. public failures use RFC 9457-compatible `application/problem+json` documents
   without raw exception, SQL, token, PII or database detail;
9. all responses carry non-content request evidence and defensive cache/content
   headers;
10. Swagger and ReDoc user interfaces are disabled in the pre-GA service.

## Alternatives considered

### Tenant headers signed by a gateway

Deferred. A correctly signed gateway assertion can be safe, but it requires a
key lifecycle, replay window, audience binding and direct-ingress exclusion. The
initial contract uses an injected authorizer so Keyverse OIDC can become the
canonical adapter.

### Static bearer token in production

Rejected. It cannot represent tenant, actor, purpose, revocation or federation
and creates a dangerous deployment fallback.

### Put authorization only in PostgreSQL

Rejected. Row-level security is defense in depth and does not authenticate a
caller or determine lawful purpose.

### Run blocking PostgreSQL operations directly in async handlers

Rejected. It can block unrelated requests on the event loop.

## Consequences

- Deployments must supply an identity adapter; the package does not boot itself
  from ambient environment variables.
- A Keyverse OIDC/JWKS adapter, revocation strategy and readiness probe remain
  separate reviewed slices.
- Ingress request-size enforcement remains required in addition to the
  application byte boundary.
- Unknown framework-generated HTTP errors are not yet guaranteed to use the
  Orgmetra problem schema and remain a documented pre-GA gap.

## Failure and recovery

Authentication and purpose failures deny access before repository invocation.
Malformed metadata and body overflows fail before a domain mutation. Repository
conflicts, authorization denials and outages map to stable 409, 403 and 503
problems. Unexpected failures return a fixed 500 response and preserve only an
opaque trace reference for operator correlation.

## Verification

- complete endpoint workflows with a repository and authorizer test double;
- absence, malformed token and purpose-denial cases;
- server-selected purpose and tenant-context assertions;
- actual and declared request-body limit probes;
- RFC 9457 problem shape and non-echo tests;
- stable OpenAPI operation identifiers and bearer security scheme;
- immutable action pins, minimal workflow permissions and no model credentials;
- exact 100% production statement and branch coverage;
- public docstring audit on Python 3.12 and 3.14.

## Security and governance impact

The API makes identity, purpose, tenant and persistence authority separate,
reviewable interfaces. It supports least privilege and evidence collection for
CSAP- and SOC 2-oriented engineering without claiming certification.
