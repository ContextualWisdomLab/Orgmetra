# Keyverse access-token profile for Orgmetra

## Customer action before enabling the adapter

Configure Keyverse to issue short-lived asymmetric access tokens for the exact
Orgmetra API audience, then provide two reviewed host adapters:

1. `JwksProvider` — supplies a bounded issuer-specific JWK Set acquired through
   an SSRF-safe, provenance-preserving connector;
2. `IdentityReferenceResolver` — maps Keyverse subject and tenant identifiers to
   opaque Orgmetra UUID references without using email as an implicit join key.

Do not expose the integration with a generic discovery URL, shared HMAC secret,
caller-selected issuer, or direct use of the external subject as a person ID.

## Required JOSE header

| Header | Contract |
| --- | --- |
| `typ` | `at+jwt` media type profile |
| `alg` | one configured asymmetric algorithm: `RS256`, `PS256`, or `ES256` |
| `kid` | one printable identifier, 1-256 characters, matching exactly one JWK |

The verifier does not accept `none`, HMAC algorithms, embedded caller keys,
multiple matching keys, encryption-use keys, or a key whose algorithm conflicts
with the token and verifier policy.

## Required claims

| Claim | Contract |
| --- | --- |
| `iss` | exact configured HTTPS issuer |
| `sub` | printable Keyverse subject identifier, 1-255 characters |
| `aud` | contains the exact configured Orgmetra API audience |
| `iat` | finite JWT NumericDate |
| `exp` | finite JWT NumericDate after `iat` |
| `nbf` | optional; verified when present |
| `jti` | printable unique token identifier, 1-255 characters |
| `orgmetra_tenant` | printable external tenant identifier, 1-255 characters |
| `orgmetra_purposes` | 1-64 unique lower-case ASCII purpose codes |

The default maximum `exp - iat` is 900 seconds and may be configured only from
60 through 3,600 seconds. Clock skew defaults to 30 seconds and is capped at 120.

## Purpose binding

The People API chooses the required purpose from route code. The authorizer does
not accept a purpose header or use a caller-provided purpose to broaden access.
It confirms that the selected purpose appears in the token and returns the full
validated purpose set for a defensive check by the API boundary.

## Identity mapping

The following identities remain distinct:

```text
Keyverse issuer + external tenant id
  -> Orgmetra tenant_record_id

Keyverse issuer + subject + external tenant id
  -> Orgmetra actor_reference

Orgmetra actor_reference
  != person_record_id unless an explicit reviewed relationship exists
```

Email, display name and mutable username are not automatic identity keys.

## Failure classification

| Failure | Public category | Customer next action |
| --- | --- | --- |
| Invalid signature/claims/header/key | authentication failed | acquire a valid access token or repair issuer configuration |
| Required purpose absent | authorization denied | request the correct purpose grant |
| Signing keys unavailable/ambiguous | identity provider unavailable | refresh or repair the key connector/cache |
| Identity mapping unavailable/invalid | identity provider unavailable | repair the tenant/subject mapping service |

The adapter never returns bearer tokens, claim documents, external subject or
tenant values, JWK material, discovery URLs or internal exception text.

## Explicitly external responsibilities

- OIDC discovery and issuer metadata validation;
- DNS/HTTP/TLS egress and redirect policy;
- JWKS cache, refresh, stale-key and compromise policy;
- token revocation and account-disable handling;
- tenant and subject mapping lifecycle;
- authentication audit and anomaly detection;
- deployment secrets, residency and incident response.
