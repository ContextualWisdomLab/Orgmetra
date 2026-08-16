# Keyverse OIDC authorizer traceability

| Requirement | Design decision | Implementation | Verification | Maturity |
| --- | --- | --- | --- | --- |
| Token cannot select verifier algorithm | asymmetric configured allowlist | `KeyverseOidcConfig`, header check | HS256 and unsupported-algorithm tests | implemented_on_active_pr |
| Token cannot select arbitrary key source | injected issuer-specific `JwksProvider` | offline authorizer | source contract has no egress/client | implemented_on_active_pr |
| One unambiguous signing key is required | exact `kid`/use/algorithm/verification-operation match | `_select_signing_key`, `_validate_key_operations` | absent, duplicate, encryption-use, incompatible `key_ops` and malformed JWK tests | implemented_on_active_pr |
| Issuer and audience are exact | strict PyJWT decode arguments | `_decode_claims` | wrong issuer/audience tests | implemented_on_active_pr |
| Tokens are short-lived and time-valid | required `exp`/`iat`, optional `nbf`, bounded skew/lifetime | authorizer and config | expired, future, non-positive and long-lifetime tests | implemented_on_active_pr |
| External identities are not HR record IDs | injected identity-reference resolver | `IdentityReferenceResolver` | successful resolution and invalid result tests | implemented_on_active_pr |
| Route operation capability is independently authorized | RFC 9068/RFC 8693 `scope` string plus server-selected scope check | `_scope_collection`, `_scope_code`, `authorize`, `AuthorizedPrincipal.allowed_scope_codes` | malformed/duplicate/oversized scope tests and purpose-cannot-enlarge-scope denial | implemented_on_active_pr |
| Route business purpose is independently authorized | bounded purpose collection plus server-selected purpose check | `_purpose_collection`, `authorize` | malformed, duplicate and missing purpose tests | implemented_on_active_pr |
| Provider outage is not caller fault | retryable identity-provider failure | dependency translation | provider/resolver outage tests | implemented_on_active_pr |
| Token and claims are not persisted/logged | verifier owns no telemetry or storage | package source | static source contract | implemented_on_active_pr |
| Verifier behavior is portable | independent typed package | package layout | Python 3.12/3.14 CI | implemented_on_active_pr |
| Production code is explained and exercised | exact coverage and docstring gates | quality workflow | coverage JSON and docstring audit | implemented_on_active_pr |
| Discovery/JWKS acquisition is SSRF-safe | separate EgressWeave-backed connector | not implemented | none | planned |
| Unknown key refresh and cache are resilient | signed bounded cache and rotation policy | not implemented | none | planned |
| Revocation and disabled accounts propagate | Keyverse lifecycle connector | not implemented | none | planned |
| Live issuer profile is conformant | Keyverse integration environment | not implemented | none | planned |
| Release artifacts are attested | hashes, SBOM and provenance | exact pins/action SHAs only | release evidence absent | planned |

`implemented_on_active_pr` must not be presented as protected-main or production
behavior until the complete dependency stack merges and integrated acceptance is
rerun on its final exact head.
