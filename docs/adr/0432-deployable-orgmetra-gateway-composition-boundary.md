# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, or Orgmetra release production-authoritative. Protected `develop` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. It currently assigns that layer API aggregation, tenant context, purpose-bound authorization, idempotency, and event-envelope handling. Protected `docs/API_CONTRACT.md` likewise says the gateway verifies Keyverse OpenID Connect evidence before generated request validation reaches a domain handler. The executable repository does not yet provide one supported deployable product-composition boundary across those independently versioned services.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their current owners. The product-composition layer is an application adapter. It may authenticate through released identity contracts, project a product principal, select an admitted owner operation, correlate requests, preserve transport semantics, and expose composition readiness. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Fresh owner-contract verification on 2026-09-21 changes the interpretation of the earlier option B:

- protected `pingora-gateway/main` still has no published immutable GitHub Release;
- root PR #1 is Draft and has an unresolved PR-introduced supplier-admission RED (`derivative 2.2.0` / `RUSTSEC-2024-0388`) plus incomplete current-head CodeQL evidence;
- the root candidate's `API_CONFIG_CONTRACT.md` v1 requires exactly one upstream and explicitly excludes route tables, user-selected destinations, credentials, retry counts, and other product semantics;
- the pg-erd migration stack contains characterized multi-route `backend` / `frontend` composition, but its own authority says that bounded migration Admin Config does **not** become a generic multi-route product policy language; and
- pingora-gateway repository authority keeps product authentication/authorization, tenancy/business routing, Keyverse identity, and application semantics outside the reusable edge-runtime boundary.

Therefore “released shared edge owner + thin Orgmetra config” is not, by itself, an executable Orgmetra product architecture. Even a future immutable release of the current generic v1 edge contract would not supply the multi-owner route/auth/composition semantics required by protected Orgmetra architecture. Reusing the pg-erd migration-specific router or copying its mutable source would violate both owner scope and the released-contract rule.

The first executable canary under #432 is Draft PR #434. Its current contract intentionally proves only immutable route admission: exact released-owner coordinates, canonical composition hashing, route-authority collision rejection, and required/optional admission. It deliberately does not implement Keyverse authentication, HR authorization, retry policy, HTTP proxying, deployment, or buyer readiness. That narrowness is an ownership constraint, not missing permission for the composition layer to invent those semantics.

## Decision drivers

The supported product boundary must:

- preserve HR bounded-context ownership and independently versioned owner APIs;
- separate generic network/transport runtime from Orgmetra product composition;
- consume only compatible released owner contracts and immutable deployment artifacts;
- keep Keyverse as identity authority while preserving downstream owner authorization;
- preserve owner idempotency, concurrency, error, retry/replay, and scientific-state semantics rather than translate them into weaker composition-local concepts;
- prevent cross-service SQL, copied sibling source/schema, and mutable owner dependencies;
- provide one supportable local and Kubernetes deployment/recovery path;
- fail closed when identity, route, owner API, transport runtime, configuration, or deployment identity is not verifiable;
- expose exact provenance for the product-composition artifact, optional shared edge runtime, admitted owner APIs, and active route generation; and
- meet applicable buyer-path performance targets while measuring edge, composition, and owner costs separately.

## Alternatives

### A. One Orgmetra-owned gateway that also reimplements generic edge runtime

Orgmetra could own routing, product authentication/composition, connection pooling, TLS, shutdown, low-level proxying, and generic edge telemetry in one service.

Rejected as the default. Product composition belongs here, but duplicating reusable connection/proxy/runtime behavior already owned by a CWL edge product creates another supplier-security and transport-runtime surface.

### B. Shared edge runtime plus configuration only

A released shared edge runtime could receive one Orgmetra configuration file containing the product route table and authentication/composition rules.

Rejected for the current owner contracts. The generic pingora-gateway v1 contract admits exactly one upstream and excludes route tables and credentials/product semantics. Its pg-erd multi-route path is a characterized migration composition and explicitly not a generic product-policy language. Treating either mutable path as a general Orgmetra composition engine would move product semantics into the wrong owner or require source/config copying.

This alternative may be reconsidered only if the shared edge owner later publishes a **domain-neutral, release-qualified composition capability** whose documented ownership includes the needed routing primitive without absorbing product authentication, tenancy/business policy, or HR authority. Orgmetra must still own its product mapping/ACL and conformance evidence.

### C. Released shared edge transport plus deployable Orgmetra product-composition application

A released shared edge runtime supplies generic transport capabilities when available. A separately deployable Orgmetra-owned composition application terminates the product contract: Keyverse consumer integration, explicit identity-to-runtime-principal projection, route-to-owner selection, owner-contract admission, context propagation, and preservation of owner HTTP/idempotency/concurrency/error/replay semantics.

**Selected.**

The Orgmetra component is intentionally thin in domain terms but is a real executable application, not merely a config file. It has no HR application tables and no cross-service SQL. It can run behind a released shared edge runtime, or in a deployment where another approved ingress supplies equivalent network transport, without changing its product contract.

### D. No product composition boundary; expose domain APIs directly

Rejected under current protected Architecture/API truth. It would distribute Keyverse consumer behavior, route discovery, product compatibility, and common request-context projection across clients. Adopting this option requires an explicit future architecture revision rather than accidental absence of a gateway implementation.

## Decision

Orgmetra will target **two explicit runtime responsibilities**:

1. **Shared edge transport runtime (external owner, optional but preferred when release-qualified):** connection handling, generic proxy transport, upstream TLS mechanics, bounded transport resources, drain/shutdown, and low-cardinality edge telemetry within its released contract.
2. **Orgmetra product-composition application (Orgmetra owner):** product-facing authentication integration, principal projection, admitted route selection, owner API compatibility, tenant/actor/purpose propagation, product readiness, and end-to-end preservation of owner semantics.

The protected name “Orgmetra Gateway” may continue to describe the buyer-visible deployment boundary, but canonical architecture reconciliation must make these internal ownership layers explicit so “Gateway” is not mistaken for one shared reverse-proxy configuration.

The product-composition application is not an HR bounded context and owns no domain persistence. Its durable state, if any, is limited to immutable/configuration/admission/audit coordinates needed to prove which product composition generation was active; HR facts and owner command receipts remain downstream.

## Product-composition contract

The implementation owner introduces a versioned product contract equivalent to `orgmetra_gateway_composition.v1`. Serialization and package/service naming are implementation details, but the following semantics are mandatory.

### Deployment identity

- Orgmetra product release/version and source identity;
- product-composition application release/artifact digest;
- composition schema version and immutable composition digest derived from the canonical semantic route projection;
- active generation/activation identity;
- shared edge owner/release/artifact digest when that runtime is present;
- Keyverse released consumer-contract identity;
- each admitted owner service release/API/OpenAPI digest; and
- environment/deployment identity containing no credential or person/tenant PII.

A Git commit may be retained as provenance but does not replace an immutable consumer/deployment release. A caller-provided digest that is not reproducibly derived from the admitted semantic projection is not configuration authority.

### Route admission

Each admitted route carries at least:

- stable `route_id`;
- HTTP path template and allowed method set;
- owning service/bounded-context identity;
- released owner API contract version and OpenAPI digest;
- immutable owner artifact/release coordinate sufficient to reconstruct the exact admitted operation contract;
- logical upstream service reference;
- required coarse product capability;
- authoritative tenant/actor/purpose input locations; and
- required-versus-optional readiness criticality.

The composition manifest **does not** mint local idempotency, concurrency, error-preservation, or retry classifications. Those semantics remain owner contract truth. When an owner exposes a released behavioral contract or receipt needed to prove those semantics, the composition generation records that exact immutable owner coordinate rather than translating it into a second taxonomy.

Admission is deny-by-default. Reachability is not admission. A route is unavailable when the released owner API is absent, incompatible, unverifiable, or does not match its recorded digest. Same-method path templates that can select the same concrete request must not coexist with different owners; parameter renaming does not make overlapping route authority distinct.

The composition application does not merge owner schemas into a monolithic domain model. Aggregated discovery is only an inventory of admitted operations.

## Authentication, identity projection, and authorization

Keyverse remains identity/issuer authority. Keyverse #155 owns durable subject-trust semantics; #158 owns the broader immutable relying-party release envelope and must reuse or completely supersede #155 rather than create parallel subject truth. Orgmetra #295/#297 own durable subject-to-Person binding/consumer ACL; Orgmetra #65 and domain owners retain purpose/resource authorization.

The product-composition application consumes those contracts and performs only the runtime projection needed for one request:

- verify through the released Keyverse consumer contract before trusting identity evidence;
- map verified `sub` to a namespaced opaque actor reference, not directly to Person identity;
- map `org` / `workspace` through an explicit versioned Orgmetra tenant/workspace ACL, never an implicit UUID cast;
- map only admitted scope semantics to coarse Orgmetra operation capabilities; and
- preserve explicit business purpose as downstream authorization input without allowing it to self-authorize.

Downstream owner services re-authorize purpose/resource/domain invariants. Caller-controlled duplicate identity coordinates that disagree with authenticated/projected coordinates fail closed.

The composition application does not invent a second token issuer. A future signed internal request-context token requires a separate versioned security design and threat-model evidence.

## Idempotency, retries, cancellation, and concurrency

The composition application never owns mutation idempotency truth. It validates required transport shape and forwards the canonical `Idempotency-Key` unchanged. The owning service remains authoritative for semantic digest, replay, committed result identity, and conflict behavior.

Automatic retry is deny-by-default at the composition layer. RFC 9110 method semantics constrain what transport replay can mean, but the composition layer does not infer positive replay safety from a local `retry_class` or from the HTTP method alone. A retry may be performed only when the exact released owner contract explicitly makes that attempted replay safe under the observed request state. Mutation replay requires the released owner contract to guarantee same-key replay safety. An ambiguous post-commit transport failure is never converted into a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, and connection loss remain distinguishable evidence. Optimistic-concurrency coordinates are forwarded unchanged. No gateway/composition-local version counter replaces owner `If-Match`, expected-version, or expected-state semantics.

## Error and scientific-state preservation

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence must never become `200`, empty data, or a generic success shell.

RFC 9457 is the preferred standard where an owner publishes Problem Details. The composition layer does not silently rewrite a different released owner error contract.

Client-visible failures exclude stack traces, credentials, restricted HR payloads, internal topology, and raw internal trace identifiers. A client-safe support reference may map to restricted telemetry.

## Operability, readiness, and recovery

Signals are separate:

- edge-runtime liveness/transport readiness;
- product-composition process liveness;
- composition-config validity;
- Keyverse/identity-contract admission;
- per-owner route/contract admission; and
- buyer product readiness.

A route-admission receipt is not buyer-readiness evidence. Buyer readiness additionally depends on the released identity/ACL path, owner authorization path, runtime/deployment health, required route set, and applicable product dependencies. A missing required route makes product readiness fail. Optional routes remain explicitly unavailable rather than disappearing silently.

Configuration activation is generation-atomic; a partially validated generation never becomes current. Rollback activates a previously admitted immutable generation and revalidates compatibility with the deployment actually selected.

The composition application must release request tasks, buffers, client/upstream connections, and temporary state on success, rejection, cancellation, timeout, partial response, and owner-unavailable paths. If a shared edge runtime is used, edge and composition drain semantics are tested together rather than each layer claiming shutdown in isolation.

## Performance evidence

Applicable commercial paths measure the complete asynchronous path, including every deployed layer:

`client/k6 -> [shared edge transport, if deployed] -> Orgmetra product composition -> owner HTTP service -> PostgreSQL -> owner -> composition -> [edge] -> client`

For paths designated applicable to the commercial target, p95 must be <= 20 ms. Evidence reports at least edge overhead, composition authentication/principal-projection/routing/serialization/upstream-client overhead, and owner authorization/query/transaction cost separately.

Do not claim the SLO from an in-memory router, mocked owner, reduced sample, discarded slow requests, disabled authentication/audit, or warm-cache-only subset. Cold/connection-establishment and steady-state windows are reported separately when materially different. Profile the measured bottleneck before changing runtime/language; Rust-first optimization follows measured material cost rather than preference.

## Security and privacy invariants

- no cross-service SQL or shared HR write repository;
- no mutable sibling source/config, floating image/tag, or copied owner schema;
- no reuse of pg-erd migration routing as a general product router without an independently released owner contract that explicitly supports that role;
- no bearer credential, restricted HR payload, tenant/person identifier, or high-cardinality sensitive value as an unbounded metric label;
- no caller-controlled header overrides contradictory authenticated identity/purpose coordinates;
- browser CORS/CSRF/cookie/session behavior is explicit when used;
- route inventory/readiness exposes safe contract coordinates without leaking secrets; and
- all composition/config/deployment changes are attributable and auditable.

## RED -> GREEN acceptance

Implementation must preserve executable RED cases for at least:

- Architecture advertises an Orgmetra Gateway but no deployable product-composition application exists;
- a released shared edge runtime exists but its contract cannot express the Orgmetra product topology;
- a pg-erd-specific migration route contract is mistakenly admitted as generic Orgmetra route authority;
- a route exists without a compatible released owner OpenAPI contract;
- a composition digest is accepted even though it is not derived from the canonical route materialization;
- two same-method route templates can select the same concrete request but claim different owners;
- composition-local retry/idempotency/concurrency classification diverges from or substitutes for owner contract truth;
- a route-admission receipt is represented as buyer/product readiness;
- decoded/unverified Keyverse claims reach product principal projection;
- token/path/query/header tenant/actor/purpose coordinates conflict and one source is silently preferred;
- coarse edge/composition admission passes while the owner would deny purpose/resource authorization;
- gateway/composition idempotency or concurrency coordinates diverge from the owner;
- an ambiguous mutation transport failure causes a second fact;
- owner denial/conflict/unavailable/timeout/scientific non-success is converted into success;
- stale or partially validated config activates;
- cancellation/error leaks connections/tasks/buffers;
- composition code can query another context's PostgreSQL schema; and
- benchmark evidence bypasses one deployed layer or the owner database while claiming buyer-path latency.

GREEN requires real deployable boundaries, immutable identity for every admitted layer, right-cleared realistic data where buyer acceptance depends on data, exact current-head tests, Podman/Colima and supported Kubernetes evidence, fault/recovery rehearsal, security evidence, and the applicable p95 target.

Draft #434 currently supplies only a focused executable canary for the route-admission subset. Its RED history verifies missing implementation, unbound config digest, noncanonical release locator, route-authority overlap, duplicated retry-policy authority, and overclaimed readiness. Local 100% unit/branch coverage on that Draft does not satisfy hosted current-head, deployment, identity, owner-contract, recovery, performance, protected-integration, or release acceptance.

## Implementation and release order

The causal order is:

1. keep #432 as the single executable owner of this product gap;
2. keep #433 Proposed until this ownership decision passes normal review/protected integration;
3. shared edge owner resolves supplier/security/current-head gate REDs and eventually publishes a release-qualified runtime before Orgmetra consumes it;
4. Keyverse #155/#158 and Orgmetra #295/#297/#65 reach the required protected/released consumer boundaries;
5. advance #434 ordinary-forward from then-current protected truth, preserving its route-admission RED/GREEN evidence without treating the current stacked Draft as shipped authority;
6. implement the deployable HTTP composition host without copying shared-edge or owner-service source;
7. consume only released shared-edge capability actually supported by its owner contract; if the released edge contract remains single-upstream/transport-only, place the Orgmetra composition application behind it rather than pretending edge config is the product router;
8. admit only compatible released owner OpenAPI/behavior contracts and preserve owner semantics end to end;
9. obtain realistic fault/security/recovery/k6 E2E evidence for the full deployed path;
10. reconcile canonical `ARCHITECTURE.md`, TRD, API, SECURITY, THREAT_MODEL, TEST_STRATEGY, OPERABILITY, TRACEABILITY, baseline, and deterministic manifest through their existing single-writer lanes; and
11. normal protected integration precedes version/tag/package/immutable Orgmetra release with SBOM, provenance, reproducibility, and rollback evidence.

## Consequences

This decision keeps generic transport runtime reusable without assigning product semantics to a reverse proxy that does not own them. It also means the phrase “thin Orgmetra composition” refers to a small **deployable application contract**, not merely a configuration document. Orgmetra carries the operational cost of one explicit product-composition service, but its boundary is inspectable, independently testable, and replaceable without moving HR truth.

The buyer-visible Gateway cannot be claimed shipped until the product-composition application, identity consumer path, required owner APIs, optional shared edge runtime, deployment provenance, recovery, and full-path performance evidence all converge on protected/released truth.

## References

The focused APA 7th standards/research record remains in `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in TRACEABILITY rather than being misrepresented as an external normative standard.