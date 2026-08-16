# Keyverse access-token profile for Orgmetra

## Customer action before enabling the adapter

Configure Keyverse to issue short-lived asymmetric access tokens for the exact
Orgmetra API audience, including the route-capability `scope` values and the
separate Orgmetra business-purpose grants required by the customer policy. Then
provide two reviewed host adapters:

1. `JwksProvider` — supplies a bounded issuer-specific JWK Set acquired through
   an SSRF-safe, provenance-preserving connector;
2. `IdentityReferenceResolver` — maps Keyverse subject and tenant identifiers to
   opaque Orgmetra UUID references without using email as an implicit join key.

Do not expose the integration with a generic discovery URL, shared HMAC secret,
caller-selected issuer, direct use of the external subject as a person ID, or an
application purpose that substitutes for OAuth operation scope.

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
| `scope` | RFC 8693 §4.2 JSON string containing 1-64 unique, space-delimited Orgmetra operation scopes; each scope is 1-128 reviewed lower-case ASCII service-vocabulary characters |
| `orgmetra_tenant` | printable external tenant identifier, 1-255 characters |
| `orgmetra_purposes` | 1-64 unique lower-case ASCII purpose codes |

RFC 9068 uses the `scope` claim for authorization scopes and points to RFC 8693
§4.2 for its JSON representation. Orgmetra intentionally keeps that standard
operation-capability grant independent from its finer application-purpose claim.
A token must carry both grants required by the route; neither can enlarge the
other.

The default maximum `exp - iat` is 900 seconds and may be configured only from
60 through 3,600 seconds. Clock skew defaults to 30 seconds and is capped at 120.

## Scope and purpose binding

The People API chooses both the required operation scope and the required
business purpose from route code. The authorizer accepts neither value from an
untrusted purpose/scope header. It validates the route-selected scope against the
standard `scope` claim, validates the route-selected purpose against
`orgmetra_purposes`, and returns both complete validated grant sets for defensive
checks by the API boundary.

Examples of operation scopes include `orgmetra.people.read` and
`orgmetra.people.write`. Higher-risk talent-acquisition or job-architecture
commands use their own reviewed scopes rather than inheriting a broad people
capability.

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
| Required operation scope absent | authorization denied | request the route capability grant for this API operation |
| Required business purpose absent | authorization denied | request the lawful business-purpose grant for this HR action |
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
