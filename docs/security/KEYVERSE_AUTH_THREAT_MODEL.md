# Keyverse authorization adapter threat model

## Scope

This model covers the offline JWT verifier, strict configuration, injected JWK
Set provider, injected identity-reference resolver, and the principal returned to
the People API. Discovery, network transport, Keyverse itself and durable identity
mapping are external trust domains.

## Assets

- accepted issuer and audience policy;
- signing-key trust anchors and key identifiers;
- external subject and tenant identifiers;
- opaque Orgmetra tenant and actor references;
- validated purpose grants;
- bearer access tokens;
- service availability and failure classification.

## Trust boundaries

```text
Untrusted bearer token
  -> compact token and JOSE header validation
  -> injected issuer-specific JWK Set
  -> signature and registered claim verification
  -> bounded private identity/purpose claims
  -> injected identity-reference mapping
  -> AuthorizedPrincipal
  -> People API defensive purpose check
```

## Threats and controls

| Threat | Control in this slice | Residual work |
| --- | --- | --- |
| Algorithm confusion | configured asymmetric allowlist and exact algorithm/key match | live issuer conformance and key-policy monitoring |
| Unsigned or HMAC token | no `none` or HS algorithms | central configuration review |
| Attacker-selected key | bounded `kid`, injected issuer-specific JWK Set, no embedded key trust | discovery/JWKS provenance and cache integrity |
| Ambiguous duplicate keys | exactly one compatible matching JWK required | connector duplicate-key alerting |
| Wrong issuer or audience | exact PyJWT issuer/audience verification | Keyverse client registration governance |
| Expired or future token | `exp`, `iat`, optional `nbf`, bounded skew | trusted host clock monitoring |
| Long-lived stolen token | configurable maximum lifetime | revocation and sender-constrained token roadmap |
| Tenant spoofing in claim | claim verified by signature, then mapped through resolver | authoritative mapping lifecycle and tenant disable |
| Mutable email used as identity | resolver accepts issuer/subject/tenant only | explicit person/account relationship workflow |
| Purpose escalation | bounded signed purpose collection plus route-selected purpose | entitlement review and least-privilege administration |
| Token/claim leakage | no logging, persistence, HTTP, environment or audit ownership | privacy-safe host telemetry and memory handling |
| SSRF/DNS rebinding | verifier owns no egress | separate EgressWeave-backed connector |
| Stale/compromised signing key | provider boundary distinguishes outage | cache/rotation/compromise policy and operational runbook |
| Key-provider outage misreported as bad login | retryable `IdentityProviderUnavailable` | readiness/degraded-state behavior and SLO |
| Mapping outage exposes identifiers | stable non-content provider error | operator-only correlation and incident controls |
| Key-set resource exhaustion | maximum 128 keys and bounded header fields | connector response-byte and parse-depth limits |
| Malformed cryptographic key | safe provider failure | connector schema validation and provenance |
| Token replay | short lifetime and required `jti` | replay detection for high-risk actions and revocation |
| Cross-service token substitution | exact audience | distinct API audiences per service |

## Abuse cases

### Token chooses `HS256`

The algorithm is rejected before JWK selection. A verifier secret is never used
as a token-signing key.

### Token points to an arbitrary JWKS URL

The token has no accepted key URL or discovery authority. Only the injected
provider for the configured issuer supplies keys.

### JWK Set contains two keys with the same `kid`

The verifier classifies the key set as ambiguous and unavailable. It does not
try keys in order or accept the first signature that verifies.

### Token contains another customer's tenant string

Signature validity alone is insufficient. The resolver maps the signed external
tenant and subject under the exact issuer to opaque Orgmetra references. Mapping
failure denies the operation without returning the identifiers.

### Page or model output supplies a bearer token or purpose

The People API's authentication boundary accepts only the HTTP bearer credential
and selects purpose from route code. LLM output has no credential or policy
authority.

## Production acceptance

- reviewed Keyverse issuer metadata and access-token conformance;
- SSRF-safe discovery/JWKS connector with bounded redirects, DNS pinning, TLS and
  response size;
- signed cache, rotation, unknown-`kid` refresh and emergency compromise policy;
- revocation/account-disable propagation;
- high-risk replay handling and `jti` observability without token retention;
- authoritative identity-link lifecycle and deprovisioning;
- live rotation/outage/recovery tests;
- memory/log/trace review for token and claim leakage;
- SBOM, provenance, vulnerability scan and independent penetration testing.
