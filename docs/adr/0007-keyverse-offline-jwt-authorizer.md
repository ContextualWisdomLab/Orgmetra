# ADR-0007: Offline strict JWT access-token authorizer for Keyverse

- Status: Proposed
- Date: 2026-08-15
- Owners: Orgmetra maintainers
- Depends on: ADR-0006
- Supersedes: none

## Context

The People API intentionally has no default production identity implementation.
Orgmetra needs a Keyverse integration without giving token verification ambient
network access, environment-owned credentials, tenant-table access, or authority
to invent HR purposes or operation capabilities. Combining discovery, DNS, HTTP
caching, JOSE verification and internal identity mapping in one component would
make the most security-critical code difficult to test and would expose it to
SSRF and key-cache failure modes.

The protected People API contract requires two independent authorization axes:
OAuth operation scope (for example `orgmetra.people.write`) and the finer lawful
HR business purpose (for example `people_admin`). RFC 9068 uses the `scope` claim
for JWT access-token authorization and delegates its JSON representation to RFC
8693 §4.2: a string containing space-delimited scopes. A business-purpose claim
must never substitute for a missing operation capability.

## Decision

Orgmetra will provide an independently importable, offline
`KeyverseOidcAuthorizer` with these boundaries:

1. a validated `KeyverseOidcConfig` fixes HTTPS issuer, audience, access-token
   type, asymmetric algorithm allowlist, claim names, clock skew and maximum
   token lifetime;
2. an injected `JwksProvider` supplies an already acquired issuer-specific JWK
   Set; the verifier performs no discovery, DNS, HTTP, cache or environment work;
3. an injected `IdentityReferenceResolver` maps external Keyverse subject and
   tenant identifiers to opaque Orgmetra UUID references;
4. JOSE routing metadata is parsed as untrusted and must contain a bounded
   `kid`, allowed `alg`, and `typ=at+jwt` profile;
5. exactly one compatible signature key may match; no symmetric algorithm,
   algorithm inference from caller input, ambiguous duplicate key, or JWK
   `key_ops` incompatible with verification is allowed;
6. signature, issuer, audience, expiration, issued-at, not-before and mandatory
   registered claims are verified;
7. token lifetime is positive and no longer than the configured maximum;
8. tenant, subject, token identifier, standard space-delimited `scope` claim and
   application-purpose collection are bounded and validated before reference
   resolution;
9. the server-selected route operation scope must be present in `scope` and the
   separately selected route purpose must be present in `orgmetra_purposes`;
10. the returned `AuthorizedPrincipal` carries both complete validated grant sets
    for a defensive API-boundary check;
11. malformed or unauthorized tokens fail as authentication/authorization;
    key-provider and identity-mapping outages fail as retryable identity-provider
    unavailability.

## Alternatives considered

### Treat business purpose as the API capability

Rejected. Purpose answers why an HR action is being performed; OAuth scope
answers which API capability the token grants. Collapsing them lets a purpose
claim enlarge token authority and diverges from the protected API contract.

### Encode JWT scope as a JSON array

Rejected for this profile. RFC 9068 points to RFC 8693 §4.2, where `scope` is a
JSON string containing a space-separated list. Vendor-specific alternatives need
an explicit versioned profile rather than silent polymorphism.

### PyJWT `PyJWKClient` inside the authorizer

Rejected. It performs network acquisition and combines egress/cache behavior with
verification. Orgmetra needs an explicit SSRF-safe connector and separately
reviewable stale-key/rotation policy.

### Accept symmetric HS256 access tokens

Rejected. A shared verification secret would also authorize token creation and
would widen the blast radius across services.

### Trust the token's algorithm or embedded JWK

Rejected. Algorithm and trust anchors are verifier policy, not token authority.

### Use external Keyverse identifiers directly as HR record identifiers

Rejected. Authentication identity and authoritative HR person/tenant identities
have different lifecycles. The resolver owns the append-only mapping.

### Treat every key or mapping outage as invalid credentials

Rejected. It would misclassify infrastructure failure as caller fault and impede
safe retry and incident diagnosis.

## Consequences

- A future `KeyverseJwksConnector` must own discovery, HTTPS, DNS-rebinding-safe
  egress, caching, refresh and provenance under a separate ADR.
- A future identity-link service must own subject/tenant mapping, deprovisioning
  and merge/split governance.
- Each People API route must supply both an operation scope and business purpose;
  neither grant can enlarge the other.
- The authorizer can be tested with generated asymmetric keys and no network.
- Token payloads, bearer strings and external identifiers are not logged or
  persisted by this package.
- Live Keyverse conformance, rotation, revocation and account-disable behavior
  remain explicit pre-GA gates.

## Failure and recovery

A bad signature, wrong issuer/audience, invalid time, malformed claim, missing
operation scope, missing purpose or unknown key fails closed. Provider and
resolver failures expose only a stable retryable error. Recovery refreshes or
repairs the external dependency; operators do not disable signature, issuer,
audience, scope, purpose or lifetime verification.

## Verification

- generated RSA signing and successful principal resolution;
- invalid signature, issuer, audience, expiration, future time and missing claim;
- malformed `typ`, `kid`, algorithm and compact-token surfaces;
- absent, duplicate, encryption-use, incompatible and malformed JWKs;
- bounded tenant, subject, `jti`, lifetime, operation-scope and purpose grants;
- purpose cannot enlarge a token lacking the route operation scope;
- insufficient scope and insufficient purpose both deny before identity mapping;
- provider/resolver outage translation without identity or endpoint leakage;
- static proof of no verifier-owned network/environment/logging authority;
- immutable action pins, minimal CI permissions, Python 3.12/3.14;
- exact 100% production statement and branch coverage and public docstrings.

## Security and governance impact

This separation narrows signing-key, network, identity and HR data trust domains.
It supports least privilege, traceable failure classification and CSAP/SOC 2-
oriented evidence without claiming certification.
