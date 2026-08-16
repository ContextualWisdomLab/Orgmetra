# People API threat model

## Scope

This model covers the `orgmetra-people-api` factory, injected identity and
repository ports, HTTP boundary, and people/candidate/worker-link/audit routes.
Keyverse acquisition/caching, PostgreSQL deployment, ingress, and customer
identity governance remain separate trust domains.

## Protected assets

- opaque tenant and actor identities;
- OAuth-style operation scopes and HR business-purpose grants;
- person and candidate records and candidate-to-worker linkage;
- effective/business time versus system-recorded time integrity;
- governed decision/evidence provenance and audit evidence;
- internal trace topology, database credentials, and service availability.

## Trust boundaries

```text
Untrusted HTTP request
  -> bounded ASGI boundary + random client support reference
  -> injected TokenAuthorizer
  -> independent scope + purpose checks
  -> server-built PurposeContext
  -> PeopleRepository port
  -> forced-RLS PostgreSQL transaction
```

The request cannot choose tenant, actor, scope, purpose, decision/evidence audit
references, or system-recorded time. `X-Correlation-Id` is bounded workflow
metadata only.

## Threats and controls

| Threat | Control in this slice | Residual work |
| --- | --- | --- |
| Tenant/actor spoofing | identities come only from authorizer | live Keyverse mapping lifecycle |
| Capability escalation | route-owned operation scope, defensively rechecked | entitlement review and token-profile conformance |
| Purpose escalation | independent route-owned HR purpose | centralized purpose administration |
| Purpose used as scope substitute | negative tests require both dimensions | live adapter must parse scope claim correctly |
| Caller-forged decision/evidence provenance | decision/evidence headers not accepted as audit authority | governed evidence resolver and sealed evidence-set contract |
| Back/future-dated system history | person command has no `recorded_at`; repository/database own knowledge time | integrated DB evidence after stack retarget |
| Internal trace disclosure | client receives random non-semantic `err_...` support reference only | privacy-safe operator trace correlation |
| Bearer-token leakage | bounded token, never echoed | TLS, revocation, secret scanning, short lifetimes |
| Cross-tenant probing | uniform not-found behavior plus RLS boundary | rate limits/anomaly detection |
| Oversized/misframed body | declared and observed ASGI byte counting | ingress limit and timeout |
| PII/SQL/credential leakage in errors | fixed problem text and validation paths without rejected values | privacy-safe structured logging |
| Event-loop starvation | synchronous repository work enters threadpool | load/backpressure evidence |
| Browser overexposure | no permissive CORS or docs UI default | explicit browser-origin policy if introduced |
| Replay of non-idempotent mutation | identity-level conflicts only | atomic idempotency-key ledger before GA |
| High-impact employment mutation without human evidence | not claimed as governed in this slice | confirmation/reason/versioned evidence required before GA |
| Audit/business divergence | repository writes audit in transaction where supported | transactional outbox and integrated rollback tests |
| Dependency drift | exact CI pins/action SHAs | hash locking, SBOM, provenance, artifact attestation |

## Abuse cases

### Valid HR purpose but missing write capability

The authorizer receives the route-selected scope and purpose. The API checks both
on the returned principal. A `people_admin` purpose without
`orgmetra.people.write` fails before repository access.

### Valid scope but wrong business purpose

A token carrying `orgmetra.people.write` cannot substitute that capability for
`people_admin`; the independent purpose check fails before repository access.

### Caller supplies decision/evidence headers

Those headers are not dependency parameters and do not populate
`PurposeContext`. A future governed workflow must resolve tenant-bound, versioned,
sealed evidence instead of trusting opaque caller strings.

### Caller tries to rewrite system history

`recorded_at` is an unknown request field and is rejected. Effective dates remain
client-specified business facts; system-recorded time is assigned by persistence.

### Caller uses a support reference to infer internal topology

Support references are random `err_...` tokens. Internal trace UUIDs, tenant IDs,
actor IDs, and decision semantics are not copied into client responses.

### Caller guesses another employee UUID

The read is constrained by authorized tenant context. Absent and invisible rows
produce the same `404` response.

## Security acceptance before production

- Keyverse scope-plus-purpose token conformance with SSRF-safe JWKS acquisition,
  issuer/audience/algorithm/time/key-rotation and revocation tests;
- atomic idempotency-key ledger and concurrency/retry/replay evidence;
- governed high-impact human confirmation, reason, and versioned evidence;
- trusted-proxy/TLS policy, tenant/actor rate limits, and bounded load evidence;
- privacy-safe OpenTelemetry and incident logging without client trace leakage;
- SAST, dependency, SBOM, provenance and container scanning;
- backup/restore, breach-response, and authorization/penetration rehearsal.
