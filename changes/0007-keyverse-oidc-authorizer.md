# Unreleased: strict Keyverse JWT authorizer

## Added

- independently importable offline Keyverse JWT access-token authorizer
- strict HTTPS issuer, audience, access-token type and asymmetric algorithm profile
- injected JWK Set and identity-reference resolver ports
- exact signing-key selection and registered/private claim validation
- bounded positive token lifetime and duplicate-free purpose collection
- retryable identity-provider failure classification
- Python 3.12/3.14 exact coverage and public docstring gate

## Security

- no verifier-owned discovery, DNS, HTTP, cache, persistence, environment or logging authority
- no HMAC, unsigned token, embedded caller key or ambiguous duplicate-key path
- external subject and tenant identifiers are mapped to opaque Orgmetra references
- token, claims, JWK material and identity strings are not copied into audit records
- CI uses minimal permissions, immutable action revisions and no model credentials

## Known limits

Discovery/JWKS acquisition, SSRF-safe egress, signed key cache and rotation,
revocation/account-disable propagation, identity-link lifecycle, live Keyverse
conformance, SBOM/provenance and external security review remain release gates.
