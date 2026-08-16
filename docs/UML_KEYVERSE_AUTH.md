# Keyverse authorization UML views

## Component boundary

```mermaid
flowchart LR
    token["Untrusted bearer token"] -->|"Compact JWT"| verifier["KeyverseOidcAuthorizer"]
    route["Server-selected route policy"] -->|"Operation scope + HR purpose"| verifier
    verifier -->|"Exact issuer"| keys["Injected JwksProvider"]
    verifier -->|"Issuer + subject + tenant"| mapping["Injected IdentityReferenceResolver"]
    keys -.->|"Future SSRF-safe adapter"| keyverse["Keyverse JWKS"]
    mapping -.->|"Future identity-link adapter"| identity["Orgmetra identity links"]
    verifier -->|"Opaque references + scopes + purposes"| principal["AuthorizedPrincipal"]
    principal -->|"Defensive scope + purpose checks"| api["Orgmetra People API"]
```

## Successful verification sequence

```mermaid
sequenceDiagram
    participant API as People API
    participant Auth as KeyverseOidcAuthorizer
    participant Keys as JwksProvider
    participant Resolver as IdentityReferenceResolver

    API->>Auth: authorize(bearer token, route scope, route purpose)
    Auth->>Auth: Validate route scope and purpose vocabulary
    Auth->>Auth: Validate compact JWT, alg, typ and kid
    Auth->>Keys: get_jwks(exact issuer)
    Keys-->>Auth: Bounded JWK Set
    Auth->>Auth: Select exactly one compatible verification key
    Auth->>Auth: Verify signature, issuer, audience and time
    Auth->>Auth: Validate tenant, subject, jti, standard scope and purposes
    Auth->>Auth: Require route scope AND route purpose independently
    Auth->>Resolver: resolve(issuer, subject, tenant external id)
    Resolver-->>Auth: Opaque tenant and actor references
    Auth-->>API: AuthorizedPrincipal(scopes, purposes)
```

## Failure classification sequence

```mermaid
sequenceDiagram
    participant API as People API
    participant Auth as KeyverseOidcAuthorizer
    participant Keys as JwksProvider
    participant Resolver as IdentityReferenceResolver

    API->>Auth: authorize(token, scope, purpose)
    alt Malformed token or bad signature/claims
        Auth-->>API: AuthenticationFailed
    else Operation scope absent
        Auth-->>API: AuthorizationDenied
    else Business purpose absent
        Auth-->>API: AuthorizationDenied
    else Keys unavailable or ambiguous
        Auth->>Keys: get_jwks(issuer)
        Keys-->>Auth: Outage or invalid key set
        Auth-->>API: IdentityProviderUnavailable
    else Identity mapping unavailable
        Auth->>Resolver: resolve external identities
        Resolver-->>Auth: Outage or invalid result
        Auth-->>API: IdentityProviderUnavailable
    end
```

These views describe active-PR architecture only. They become protected-main
truth after dependency merges and fresh integrated review and checks.
