# Gateway composition boundary traceability

Verification date: 2026-09-21

Related issue: #432

Related Proposed ADR: `docs/adr/0432-deployable-orgmetra-gateway-composition-boundary.md`

## Protected-truth RED

Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` documents an Orgmetra Gateway in `ARCHITECTURE.md` and gives it pre-handler Keyverse validation responsibility in `docs/API_CONTRACT.md`. The executable repository does not yet expose one supported deployable composition artifact across independently versioned Orgmetra domain services. This document records design/acceptance traceability only; it does not convert the RED into shipped capability.

Fresh shared-owner and identity-owner evidence on 2026-09-21:

- `ContextualWisdomLab/pingora-gateway` protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` has no published immutable GitHub Release.
- root PR #1 exact `38db1949354f5721dc0ecfeea395bcf958a64ace` remains Draft and records an unresolved PR-introduced OSV finding (`derivative 2.2.0` / RUSTSEC-2024-0388) plus incomplete exact-head central CodeQL evidence.
- `ContextualWisdomLab/keyverse` protected `main@7d9151cd2da260e118020c938c7358e2ee75d541` also has no published immutable GitHub Release.
- protected Keyverse deliberately keeps the OIDC relying-party mapper profile closed: one self-pinned audience plus only canonical `role`, `org`, and `workspace` hardcoded claims when mappers are present. Orgmetra must not widen that profile ad hoc with HR-specific tenant/actor claims.
- Keyverse #155 already owns subject-assertion trust semantics for durable RP binding, including durable-versus-session-only subject-correlation eligibility. Keyverse #158 is the broader immutable OIDC relying-party release envelope and must adopt/reuse #155 rather than create a second subject-trust schema.
- protected Orgmetra People and Job Analysis HTTP edges currently expose an injected `TokenAuthenticator`/`AuthenticatedPrincipal` port rather than a released Keyverse verifier/ACL. The principal requires an Orgmetra tenant UUID, opaque actor reference, and explicit Orgmetra operation scopes, so Keyverse identity coordinates require an explicit Orgmetra-owned mapping rather than an implicit claim cast.
- Orgmetra #295/#297 already own the subject-binding/consumer ACL boundary and released-Keyverse prerequisite for durable Person correlation; Orgmetra #65 owns purpose-bound authorization runtime integrity. Gateway principal projection may compose these contracts but must not duplicate their authority.
- therefore no mutable gateway or identity-provider branch, PR commit, copied source/config, floating image, decoded-only claim set, guessed identity mapping, or parallel subject/authorization schema is an admissible Orgmetra production dependency.

## Context Map

```mermaid
flowchart LR
    client[Orgmetra workspaces / API clients]
    gateway[Shared released edge runtime\n+ Orgmetra composition contract]
    keyverse[Keyverse released OIDC contract\n#155 semantics + #158 release]
    identity_acl[Orgmetra identity ACL\n#295/#297]
    authz[Orgmetra purpose authorization\n#65 + domain owners]
    people[people_core]
    org[organization_core]
    jobs[job_architecture]
    talent[talent acquisition / talent owners]
    perf[performance_management]
    assess[assessment_coordination]
    validation[workforce_validation]

    client --> gateway
    gateway -. verify released identity contract .-> keyverse
    gateway --> identity_acl
    identity_acl --> authz
    authz --> people
    authz --> org
    authz --> jobs
    authz --> talent
    authz --> perf
    authz --> assess
    authz --> validation
```

The gateway is an application/edge adapter, not a bounded context for HR truth. Keyverse remains issuer/identity authority. Keyverse #155 owns durable subject-trust semantics; #158 packages the broader released RP handoff without replacing #155 by declaration alone. Orgmetra #295/#297 own subject-binding/ACL semantics, while #65 and each domain owner retain purpose/resource authorization. Any gateway-specific principal projection is a composition adapter over those released/protected contracts, not a new identity or authorization owner.

## Ownership matrix

| Concern | Owner | Gateway / ACL role | Forbidden behavior |
|---|---|---|---|
| Identity provider, credentials, token issuance, canonical OIDC profile | Keyverse | Validate released OIDC contract | Store credentials/passkeys; become a second identity issuer |
| Durable-versus-session-only subject trust / RP correlation eligibility | Keyverse #155, consumed by #158 release envelope | Preserve exact released semantics | Assume every syntactically valid `sub` is durably bindable; create a parallel subject receipt |
| Immutable domain-neutral RP consumer release/profile/artifact | Keyverse #158 | Consume only protected/released artifact/profile | Replace #155 semantics; consume mutable Keyverse source/config |
| Durable subject-to-Person binding candidate / consumer ACL | Orgmetra #295/#297 | Reconstruct/revalidate released Keyverse evidence before positive binding | Let gateway or Keyverse mint Person truth; trust locally forgeable candidate data |
| Keyverse `sub`/`org`/`workspace` to runtime Orgmetra actor/tenant projection | Orgmetra composition ACL, constrained by #295/#297 | Produce explicit authenticated principal coordinates after cryptographic verification | Add ad hoc Keyverse HR claims; implicit UUID cast; trust decoded-only claims |
| Purpose/resource authorization runtime integrity | Orgmetra #65 + domain owners | Forward verified context and re-authorize downstream | Treat `role` or `scope` as self-authorizing HR purpose; bypass owner authorization |
| Person/Employment/Assignment | People | Route and preserve authenticated context | Read/write People tables; decide HR invariants |
| Organization/Position | Organization | Route and preserve context | Read/write Organization tables; synthesize capacity truth |
| Job/FJA/KSAO | Job Architecture | Route and preserve context | Copy job schema or ontology truth |
| Selection/Talent | owning Talent context | Route and preserve context | Make autonomous employment decisions |
| Assessment assignment intent | assessment coordination | Route and preserve context | Own assessment session/scoring/result truth |
| Scientific validity/fairness | Workforce Validation | Route and preserve state/errors | Convert pending/not-verifiable/non-convergence to success |
| Authentication journey | Orgmetra product | Terminate/mediate product transport | Replace product UX with generic proxy behavior |
| Generic proxy/runtime | released shared gateway owner | Execute supported runtime contract | Import mutable shared source into Orgmetra |
| Route/admission/config truth | Orgmetra | Own versioned composition contract | Hide owner contract/version behind floating discovery |
| Mutation idempotency/concurrency | owning domain service | Forward exact coordinates | Mint divergent replay/version truth |

## Composition manifest semantics

The implementation artifact must preserve at least the following semantic coordinates. Names are descriptive, not a frozen serialization schema.

| Coordinate | Why it exists | Acceptance |
|---|---|---|
| `composition_schema_version` | Evolves product composition without silent shape drift | Unknown major fails closed |
| `orgmetra_release` + source identity | Binds product behavior to released product evidence | Mutable/default-branch-only identity is non-production |
| `composition_digest` | Identifies exact route/policy generation | Runtime-reported digest equals deployment evidence |
| shared gateway owner/release/contract/artifact digest | Admits a reusable edge runtime | Missing/unreleased/floating identity fails closed |
| Keyverse release/contract/profile identity | Binds authentication to released issuer semantics | Missing/unreleased/incompatible identity contract fails closed |
| Keyverse subject-trust contract/version | Distinguishes durable correlation from session-only identity | #158 release must preserve/reuse #155 semantics; incompatible/missing semantics fail closed |
| Orgmetra identity-ACL version/digest | Makes identity projection reviewable and replayable | Must compose #295/#297 rather than invent a second durable-binding truth |
| `route_id` | Stable operational/audit coordinate | Unique within one generation |
| path + method set | Declares exposed operation | Must match compatible released owner OpenAPI |
| owner service + owner API release + OpenAPI digest | Keeps route tied to domain owner | Digest/version mismatch prevents admission |
| logical upstream service reference | Resolves deployment target without copying implementation | Cannot be cross-service SQL or mutable source path |
| coarse scope/capability | Early denial before owner call | Cannot enlarge token authority |
| authoritative tenant/actor/purpose locations | Prevents identity-source ambiguity | Contradiction fails closed |
| idempotency mode | Prevents edge-local replay truth | Mutation key forwarded unchanged; owner remains authority |
| concurrency/error preservation | Keeps owner invariants visible | No local version counter or success coercion |
| retry class | Makes ambiguous failure behavior explicit | Default deny for mutations without released replay contract |
| readiness criticality | Separates required from optional product routes | Missing required route makes product unready |

## RED -> GREEN evidence map

| RED / risk | Required GREEN evidence | Owner lane |
|---|---|---|
| Architecture advertises gateway but no deployable composition exists | one supported local + Kubernetes composition artifact bound to immutable identities | #432 implementation successor |
| shared gateway has no release | immutable shared-owner version/tag/artifact + SBOM/provenance/reproducibility/rollback | `pingora-gateway` owner stack |
| shared runtime exact security RED | owner root-cause fix and exact-head security evidence; no advisory suppression | `pingora-gateway` owner stack |
| Keyverse durable-subject trust and broader RP release are separate open owner gaps | #155 semantics protected/released or completely inherited by verified successor; #158 immutable release envelope adopts that contract without parallel schema | Keyverse #155 -> #158 |
| Keyverse has no immutable RP consumer release | released OIDC/profile contract + immutable artifact + conformance fixtures + SBOM/provenance/rollback | Keyverse #158 |
| raw/locally constructible subject evidence becomes durable Person binding | positive binding only after released owner evidence is reconstructed/revalidated; wrong/stale/forged/cross-tenant/non-durable evidence fails closed | Orgmetra #295/#297 |
| Keyverse canonical identity claims do not directly equal Orgmetra runtime principal coordinates | explicit versioned composition ACL maps verified `sub` to opaque actor, `org`/`workspace` to tenant/workspace binding, and released scopes to allowed operation capabilities without duplicating #295/#297 durable-binding truth | #432 implementation successor + #295/#297 |
| decoded or unverified Keyverse claims are trusted | cryptographic issuer/audience/signature/algorithm/time/JWKS verification before ACL evaluation | Keyverse #158 + Orgmetra conformance |
| unknown/stale JWKS key races refresh | deterministic fail closed or bounded standards-conformant refresh; never unsigned/stale-unbounded acceptance | Keyverse #158 + gateway security test |
| role/scope bypasses purpose/resource authorization | downstream #65/domain-owner authorization executes on exact request context and denial is preserved | #65 + domain owner + gateway E2E |
| route exposed without released owner API | startup/admission test rejects missing/floating/incompatible owner contract | #432 implementation successor |
| OpenAPI digest differs from admitted contract | route remains unavailable; readiness evidence names safe route/contract coordinate | #432 implementation successor |
| token issuer/audience/signature/expiry/subject/tenant/actor invalid | request rejected before owner call | gateway security contract + identity ACL |
| token/path/query/header tenant/actor/purpose contradict | deterministic fail-closed rejection; no source precedence guess | gateway + identity ACL + owner contract |
| gateway coarse scope passes but owner purpose/resource rule denies | owner denial preserved; no edge override | gateway E2E + domain owner test |
| gateway mints/changes mutation idempotency coordinate | negative test proves exact client key reaches owner and gateway stores no replay fact | gateway E2E + owner API |
| same key but owner semantic digest differs | owner conflict preserved | owner API + gateway pass-through |
| connection fails after possible mutation commit | no fresh-key automatic replay; only owner-declared same-key replay semantics may run | gateway fault-injection E2E |
| optimistic-concurrency coordinate stale | owner conflict/status preserved | gateway E2E + owner API |
| owner returns authorization/conflict/unavailable/timeout | owner status/versioned error identity preserved; never `200`/empty | gateway E2E |
| owner reports `verification_pending`/`not_verifiable`/non-convergence | semantic state remains distinguishable end-to-end | Workforce Validation/assessment E2E |
| cancelled/timeout/partial response leaks resources | socket/task/pool cleanup evidence under fault injection | gateway runtime test |
| product readiness claims success with missing required route | readiness fails and identifies non-admitted safe route coordinate | operability test |
| stale config activates partially | generation-level validation prevents partial activation | config activation test |
| rollback routes new contract to old owner silently | immutable prior generation activation + compatibility revalidation | recovery rehearsal |
| gateway can reach peer PostgreSQL directly | network/config and code test prohibit cross-service SQL | security/integration test |
| benchmark measures router stub | k6/E2E reaches gateway -> owner HTTP -> PostgreSQL with exact deployment evidence | performance acceptance |

## Identity projection invariants

The Keyverse/Orgmetra boundary is an ACL, not a Shared Kernel and not a reason to broaden the Keyverse claim surface.

- Keyverse #155 semantics determine whether an authenticated subject mode is eligible for durable RP correlation; #158 cannot silently broaden that condition.
- Orgmetra #295/#297 remain the durable subject-binding consumer path; the gateway cannot create Person binding authority merely because it can authenticate a request.
- verified Keyverse `sub` can become a namespaced opaque runtime Orgmetra actor reference only through an explicit versioned composition mapping; that actor reference is not a Person record identifier.
- Keyverse `org` and `workspace` evidence is resolved through an explicit Orgmetra mapping/version into the applicable Orgmetra tenant/workspace coordinate; a text claim is never cast directly to `tenant_record_id`.
- only explicitly admitted Keyverse scope semantics can map to Orgmetra operation capabilities; downstream #65/domain-owner purpose/resource authorization still runs.
- Keyverse `role` can contribute identity/authorization evidence but cannot create an HR business purpose, employment decision, or domain permission by itself.
- caller-controlled `X-Tenant-Reference`, `X-Actor-Reference`, path or query values must agree with the authenticated/ACL-derived coordinates when that route's contract requires them; disagreement fails closed.
- an unavailable/incompatible Keyverse release, verifier, JWKS set, subject-trust contract, or ACL mapping is authentication/admission failure, never anonymous fallback.

## Retry and failure interleavings

The implementation tests at least these ordered failures rather than only happy-path request/response.

1. owner commits mutation, response is lost, gateway observes transport failure;
2. gateway receives a client retry with the exact same `Idempotency-Key`;
3. owner replay contract returns the original committed identity;
4. gateway preserves that response without creating another mutation identity.

A companion negative case uses an owner route that does not publish replay safety. After the ambiguous transport failure, the gateway does not invent an automatic retry.

Additional interleavings:

- generation N validates while generation N+1 begins validation: only one complete generation activates at a time;
- required owner contract changes between config build and activation: digest mismatch blocks activation;
- optional owner becomes unavailable after activation: route is explicitly unavailable while required-route readiness semantics remain deterministic;
- request cancellation races owner response: cleanup happens once, and a late owner completion cannot be reported as client success after cancellation;
- token/JWKS refresh races a request: a failed/unknown key does not downgrade to unsigned or stale-unbounded acceptance; and
- a Keyverse identity-to-tenant ACL version changes while a request is in flight: one request is evaluated against one exact verified token + ACL version and cannot mix old/new projection coordinates.

## Performance evidence

The measured ordinary buyer path is:

`k6/client -> shared gateway runtime -> owner HTTP service -> PostgreSQL -> owner -> gateway -> client`

For paths designated applicable to the commercial latency target:

- target: p95 <= 20 ms;
- record sample size, concurrency, duration, deployment identity, dataset/right-to-use, PostgreSQL/schema/index/RLS state, auth/audit state, Keyverse release/profile and Orgmetra ACL identity, gateway release/artifact digest, composition digest, owner API release/OpenAPI digest, hardware/runtime, and observation timestamps;
- report gateway overhead separately from owner execution;
- report connection-establishment/cold and steady-state windows when they differ materially;
- do not discard slow requests, shrink the sample to make the target pass, disable auth/audit, or substitute an in-memory owner/router.

A failed target triggers profile evidence across DNS/connect/TLS or service-connect, gateway queueing, auth/JWKS validation, identity ACL evaluation, serialization, upstream pool acquisition, owner authorization/query/transaction, forwarding, and cleanup before any runtime/language replacement.

## Deployment and recovery evidence

GREEN requires both supported development and production-oriented composition:

- Podman/Colima local composition with production-equivalent service boundaries;
- supported Kubernetes manifests/packaging with immutable image/artifact identities;
- PostgreSQL with owner schemas/roles rather than cross-schema gateway credentials;
- immutable released Keyverse identity/profile coordinates, preserved #155 subject-trust semantics, and a versioned Orgmetra identity ACL alongside the gateway composition generation;
- separate liveness, config-validity, identity-contract admission, route-admission, and product-readiness signals;
- bounded graceful shutdown and in-flight drain;
- immutable generation activation/rollback;
- rollback rehearsal proving the restored generation still admits exactly the compatible identity and owner contracts it claims; and
- logs/metrics/traces that avoid raw credentials, restricted-HR payloads, stack traces in client responses, and unbounded tenant/person labels.

## Canonical single-writer handoff

This PR must not edit the existing canonical surfaces owned elsewhere:

- #51: `ARCHITECTURE.md`, TRD, API_CONTRACT, SECURITY, THREAT_MODEL, TEST_STRATEGY, OPERABILITY, TRACEABILITY and deterministic manifest reconciliation;
- #100: `docs/product-technical-gap-baseline.md`;
- #427: Workforce Validation HTTP semantics;
- Keyverse #155: durable subject-assertion trust semantics;
- Keyverse #158: broader immutable OIDC relying-party consumer release, reusing/subsuming #155 only with complete verified inheritance;
- Orgmetra #295/#297: durable subject-binding consumer ACL and released-owner prerequisite;
- Orgmetra #65: purpose-bound authorization runtime integrity; and
- domain-owner PRs: owner OpenAPI/domain contract truth.

After ADR 0432 is protected, #51 may reconcile the selected target architecture into canonical docs. #100 may move `API-01` only when protected/released evidence justifies a state change. A Proposed/Draft ADR is not shipment. Keyverse #155/#158 and Orgmetra #295/#297/#65 remain their own owner lanes; #432 may compose them but cannot source-copy or supersede them by implication.