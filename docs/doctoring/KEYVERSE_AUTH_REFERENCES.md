# Keyverse authorization references

This note records primary standards and technical documentation used for
ADR-0007. The references support a strict access-token verifier; they do not
establish Keyverse conformance or deployment certification.

## Decision traceability

| Decision | Primary basis | Repository evidence |
| --- | --- | --- |
| JWT signature and registered claim verification | RFC 7519; RFC 8725 | `authorizer.py`, registered-claim and signature tests |
| Keys arrive as an issuer-specific JWK Set | RFC 7517 | `JwksProvider`, exact key-selection tests |
| Access-token media type and short-lived profile | RFC 9068 | `typ=at+jwt`, audience and lifetime contract |
| Exact issuer/audience/subject validation | OpenID Connect Core; RFC 9068 | `KeyverseOidcConfig`, decode policy and tests |
| Algorithm allowlist is verifier policy | RFC 8725 | asymmetric configuration and HS256 rejection |
| Provider acquisition is outside verifier | RFC 8725 trust-boundary guidance; SSRF risk separation | offline package source contract |

## APA 7 references

Jones, M., Bradley, J., & Sakimura, N. (2014). *OpenID Connect Core 1.0
incorporating errata set 2*. OpenID Foundation.
https://openid.net/specs/openid-connect-core-1_0.html

Jones, M., Bradley, J., & Sakimura, N. (2015a). *JSON Web Key (JWK)*
(RFC 7517). Internet Engineering Task Force.
https://doi.org/10.17487/RFC7517

Jones, M., Bradley, J., & Sakimura, N. (2015b). *JSON Web Token (JWT)*
(RFC 7519). Internet Engineering Task Force.
https://doi.org/10.17487/RFC7519

Lodderstedt, T., McGloin, M., & Hunt, P. (2021). *OAuth 2.0 access token JWT
profile* (RFC 9068). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9068

Sheffer, Y., Hardt, D., & Jones, M. (2020). *JSON Web Token best current
practices* (RFC 8725). Internet Engineering Task Force.
https://doi.org/10.17487/RFC8725

PyJWT contributors. (2025). *PyJWT usage examples*.
https://pyjwt.readthedocs.io/en/stable/usage.html

## Interpretation limits

- RFC 9068 defines an interoperable OAuth access-token profile; Keyverse's actual
  claims and grant policy still require conformance evidence.
- RFC 7517 `kid` is a hint, not an authorization decision. Orgmetra additionally
  requires exactly one compatible configured key.
- Unverified JOSE headers are used only to select among already trusted issuer
  keys; they are never treated as verified claims.
- PyJWT documentation is implementation guidance. Exact pinned version behavior
  and executable tests remain authoritative for the active PR.
