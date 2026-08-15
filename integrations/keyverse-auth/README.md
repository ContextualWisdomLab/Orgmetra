# orgmetra-keyverse-auth

`orgmetra-keyverse-auth` verifies JWT access tokens for the Orgmetra People API
without owning network egress, credentials, tenant records, or employment data.
It implements the People API `TokenAuthorizer` port and returns opaque Orgmetra
tenant and actor references only after strict token and purpose validation.

## Security boundary

The package is deliberately **offline**:

- an injected `JwksProvider` supplies an already acquired key set;
- an injected `IdentityReferenceResolver` maps external Keyverse subject and
  tenant identifiers to Orgmetra UUID references;
- the verifier performs no discovery, DNS, HTTP, caching, persistence, logging,
  or environment-variable access;
- a future connector must use SSRF- and DNS-rebinding-safe egress and preserve
  issuer/key provenance.

## Token contract

The initial profile requires:

- exact HTTPS issuer and audience;
- JOSE header `typ=at+jwt`;
- configured asymmetric signing algorithm, default `RS256`;
- a bounded non-empty `kid` selecting exactly one signing JWK;
- claims `iss`, `sub`, `aud`, `exp`, `iat`, and `jti`;
- configured tenant and purpose claims;
- a positive token lifetime no longer than the configured maximum;
- the route-selected purpose to appear in the token's purpose collection.

Malformed, expired, ambiguous, wrongly signed, wrong-issuer, wrong-audience and
insufficient-purpose tokens fail closed. Provider or identity-resolution outages
return `IdentityProviderUnavailable` so the People API can emit a retryable 503
instead of misclassifying an infrastructure failure as bad credentials.

## Production gaps

- Keyverse discovery/JWKS fetch and refresh connector;
- SSRF-safe egress through EgressWeave or an equivalent reviewed boundary;
- revocation, account-disable and emergency key-compromise handling;
- signed key-cache persistence and stale-key policy;
- tenant/subject reference lifecycle and deprovisioning;
- live Keyverse conformance and rotation tests;
- deployment SLO, incident response, SBOM and provenance evidence.
