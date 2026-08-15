# People API threat model

## Scope

This model covers the `orgmetra-people-api` application factory, its injected
identity and repository ports, HTTP request boundary, and explicit people,
candidate, worker-link and audit routes. Keyverse, PostgreSQL deployment,
network ingress and customer identity governance are external trust domains.

## Protected assets

- tenant and actor identity;
- authorized HR purpose;
- person and candidate records;
- candidate-to-worker identity linkage;
- decision and evidence references;
- reference-only audit evidence;
- database credentials and service topology;
- availability of the shared service.

## Trust boundaries

```text
Untrusted HTTP request
  -> bounded ASGI request boundary
  -> injected TokenAuthorizer
  -> server-selected PurposeContext
  -> PeopleRepository port
  -> forced-RLS PostgreSQL transaction
```

The request cannot provide a tenant or purpose. Optional correlation, decision
and evidence headers are metadata only and are validated before repository use.

## Threats and controls

| Threat | Control in this slice | Residual work |
| --- | --- | --- |
| Tenant spoofing through headers | no tenant header; authorizer returns opaque tenant | production Keyverse token verification and audience binding |
| Purpose escalation | route-owned purpose constant plus defensive principal check | centralized policy administration and entitlement review |
| Bearer-token leakage | token is bounded, never logged or returned | TLS termination, secret scanning, token revocation and short lifetime |
| Cross-tenant resource probing | uniform not-found behavior plus forced database RLS | rate limits and anomaly detection |
| Oversized or misleading body framing | declared and actual ASGI byte counting | ingress limits and request timeout |
| PII leakage in errors | fixed problem detail and validation paths without values | structured privacy-safe operator logging |
| SQL or credential leakage | stable repository exceptions | centralized incident correlation and access review |
| Event-loop starvation | synchronous repository calls use threadpool | measured pool bounds and backpressure evidence |
| Permissive browser access | no CORS middleware or docs UI default | explicit customer origin policy if a browser client is introduced |
| Static-token production fallback | no built-in runtime composition or static authorizer | deployment policy and configuration attestation |
| Audit/business divergence | same database transaction in repository | transactional outbox for external event delivery |
| Trace correlation abuse | server generates trace; optional correlation is bounded UUID | replay/duplicate workflow policy |
| Framework error inconsistency | explicit domain and validation errors use RFC 9457 | normalize unknown route/method errors before GA |
| Dependency supply-chain drift | exact test pins and full action SHAs | hashes/attestations, SBOM and artifact provenance |

## Abuse cases

### Caller sends another tenant identifier

There is no accepted tenant field or header. Unknown body fields fail schema
validation. The authorizer's tenant is used for every repository operation.

### Caller submits a valid token for the wrong purpose

The route asks the authorizer for its fixed purpose and then independently checks
that the returned principal contains that purpose. Repository access never runs.

### Caller guesses an employee UUID

The read is constrained by the authorized tenant. A row absent from that tenant
and a row belonging to another tenant both produce the same `404` document.

### Caller injects names or exception text into invalid data

Validation returns only field paths and issue codes. Repository and unexpected
errors return fixed text and an opaque trace reference.

### Caller streams more bytes than declared

The middleware counts observed ASGI body bytes and refuses the request. The
deployment must also enforce an ingress limit because application-level limits
are defense in depth.

## Security acceptance before production

- Keyverse OIDC discovery/JWKS implementation with SSRF-safe egress;
- issuer, audience, algorithm, expiration, not-before and key-rotation tests;
- revocation and account-disable behavior;
- trusted-proxy and TLS policy;
- tenant and actor rate limits;
- bounded threadpool/load tests and overload response;
- privacy-safe OpenTelemetry and incident logging;
- SAST, dependency, SBOM, provenance and container scanning;
- independent penetration and authorization testing;
- backup/restore and breach-response rehearsal.
