# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

Verification date: 2026-09-22

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, or Orgmetra release production-authoritative. Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. It assigns that buyer-visible boundary API aggregation and pre-handler Keyverse integration, but the protected executable repository still does not provide one supported deployable product-composition application across independently versioned owner services.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture/FJA/KSAO, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their existing owners. Product composition is an application adapter. It may consume released identity contracts, project a product principal, select admitted owner operations, correlate requests, preserve transport semantics, and expose composition readiness. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Fresh evidence still shows protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` and no published immutable GitHub Release. Its generic v1 contract remains transport-oriented and does not transfer Orgmetra product routing, identity, tenancy, or HR policy authority.

Keyverse protected `main@7d9151cd2da260e118020c938c7358e2ee75d541` likewise has no published immutable consumer release. Keyverse #155/#158, Orgmetra #295/#297, Orgmetra #65, and domain API owners therefore remain prerequisite owners rather than copied source inside composition.

Draft #434 is the first executable canary under #432. Current exact authority is `9ced14ae97f8c07285cdc3975f57a81c717313a2`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`, with 110 ordinary-forward commits / 17 files confined to `services/product-composition-api/**`. It proves only a route-admission and structural generation-integrity slice. It does not claim Keyverse authentication, HR authorization, HTTP proxying, durable activation, Kubernetes deployment, buyer-path latency, protected integration, or release completion.

## Decision drivers

The supported boundary must preserve HR bounded-context ownership, consume only immutable released owner contracts, keep Keyverse as identity authority, preserve downstream authorization and replay/concurrency/error/scientific semantics, prohibit cross-service SQL and mutable sibling dependencies, support local/Kubernetes operation and recovery, fail closed when any identity/route/release/configuration/deployment coordinate is unverifiable, expose exact provenance, and measure the complete deployed buyer path.

## Alternatives

### A. Orgmetra-owned gateway also owns generic edge runtime

Rejected as the default. Product composition belongs in Orgmetra, but duplicating reusable TLS/connection/proxy/drain mechanics creates another transport and supplier-security surface.

### B. Shared edge runtime plus configuration only

Rejected for current owner contracts. The current generic edge contract does not provide the multi-owner product semantics Orgmetra needs. Reusing mutable migration routing would move product semantics into the wrong owner.

This option may be revisited only if the shared-edge owner publishes a domain-neutral, release-qualified capability without absorbing product authentication, tenancy/business policy, or HR authority.

### C. Released shared edge transport plus deployable Orgmetra product composition

Selected. A released shared edge supplies generic transport when available. A separately deployable Orgmetra application terminates the product contract: released Keyverse consumer integration, explicit identity-to-runtime-principal projection, route-to-owner selection, owner-contract admission, context propagation, readiness, activation/re-admission, and preservation of owner HTTP/idempotency/concurrency/error/replay semantics.

### D. Expose domain APIs directly with no product composition boundary

Rejected under current protected Architecture/API truth. Choosing this direction requires a future explicit architecture revision rather than accidental absence of an implementation.

## Decision

The buyer-visible “Orgmetra Gateway” has two internal responsibilities:

1. **Shared edge transport runtime, externally owned and optional unless a deployment requires it:** connection/proxy/TLS mechanics, bounded transport resources, drain/shutdown, and low-cardinality transport telemetry within its released contract.
2. **Orgmetra product-composition application:** product-facing authentication integration, principal projection, admitted route selection, owner API compatibility, tenant/actor/purpose propagation, product readiness, activation/re-admission, and end-to-end preservation of owner semantics.

The Orgmetra component is an application adapter, not an HR bounded context. It owns no HR application tables and no cross-service SQL. Durable state, when introduced, is limited to immutable configuration/admission/activation/audit coordinates needed to prove which exact composition generation was active.

## Product-composition contract

The implementation owner introduces a versioned contract equivalent to `orgmetra_gateway_composition.v1`.

### Deployment and generation identity

The contract binds Orgmetra product release/source identity, composition release/artifact digest, schema/config/generation/activation identity, optional shared-edge release, released Keyverse consumer-contract identity, every admitted owner API/OpenAPI/release identity, and environment/deployment identity containing no credential or person/tenant PII.

A Git commit may be provenance but does not replace an immutable consumer/deployment release. A caller-provided digest that is not reproducibly derived from admitted semantic material is not configuration authority.

One canonically constructed generation cannot be rewritten into another semantic generation. `generation_id`, schema identity, and canonical configuration digest remain bound to one lineage. The current Python canary enforces only process-local structural integrity; production activation/rollback requires durable immutable generation/configuration/deployment evidence and historical no-reassignment.

### Route admission

Each admitted route carries a stable `route_id`, exact product path template and declared method set, owning service/bounded-context identity, released owner API/OpenAPI/artifact/release coordinates, owner-bound logical upstream, coarse product capability, authoritative tenant/actor/purpose input locations, and required/optional readiness criticality.

All routes for one owner `service_id` in one generation reference one exact `OwnerApiRelease`. Simultaneous versions of one service require a future version-qualified upstream identity rather than ambiguity in the current key.

The manifest does not mint local retry, idempotency, concurrency, or error-preservation classifications. Those remain released owner truth. Admission is deny-by-default. Reachability is not admission. Invalid route material fails before configuration identity is minted.

### Bounded OpenAPI route profile

Protected Orgmetra HTTP contract truth remains OpenAPI **3.2.0**. OpenAPI Specification 3.2.1 is the current patch-level reference for the same 3.2 feature set; citing it does not upgrade protected Orgmetra truth.

The #434 canary intentionally implements a stricter product route profile than the complete OpenAPI 3.2 grammar. It admits restricted ASCII literal segments, whole-segment lower-snake-case template expressions, and exactly `DELETE`, `GET`, `HEAD`, `OPTIONS`, `PATCH`, `POST`, `PUT`. OAS-valid forms outside that profile—including mixed literal/template path segments, unsupported RFC 3986 `pchar` forms, `TRACE`, `QUERY`, and `additionalOperations` methods—fail closed before configuration identity.

This restriction is an Orgmetra product decision, not an OpenAPI requirement. Broadening it requires a released owner need plus explicit conformance tests. Framework acceptance alone is not evidence.

### OpenAPI path identity, Path Item ownership, and deterministic matching

OpenAPI 3.2 Sections 4.8.1, 4.8.2, and 4.9.1 define path identity, templating, and Path Item structure. The composition rules are:

- `/v1/people/{person_record_id}` and `/v1/people/{worker_record_id}` are one path hierarchy and cannot coexist as distinct path identities, even when methods are disjoint;
- distinct HTTP methods may coexist under the same exact template string only when they bind the same exact `OwnerApiRelease` in the current Orgmetra profile;
- a concrete path may coexist with its templated counterpart only when both routes bind the same exact `OwnerApiRelease` and declare the same exact method set;
- cross-owner concrete/template overlap remains invalid;
- overlapping templated paths without a defined winner remain fail-closed; and
- one path cannot repeat the same template expression.

One-owner-per-Path-Item is an Orgmetra fail-closed ownership rule, not an OpenAPI claim about repositories or bounded contexts. A Path Item contains shared `$ref`, summary/description, servers, parameters, and operations; path-level servers service all operations and Path Item parameters apply across the operations. The current canary has no released cross-owner merge/conformance contract for those shared fields, so disjoint methods do not make a cross-owner exact-path split safe. A future exception requires a versioned contract that defines and tests reconciliation of every shared Path Item semantic.

The same-method-set restriction for concrete/template overlap prevents composition from inventing fallback to a templated operation when OpenAPI has already selected a concrete Path Item that does not declare the method. Broader fallback semantics require explicit released-owner conformance evidence.

### HTTP operation authority

After Path Item ownership, path identity, and deterministic path matching are valid, operation ownership is checked independently. Path templates that can select the same concrete request must not split one effective method authority across different owners. For collision ownership, `GET` and `HEAD` form one selected-resource authority because RFC 9110 Section 9.3.2 defines HEAD as GET semantics without response content. Canonical route material still preserves the methods actually declared; this rule does not synthesize an undeclared HEAD operation.

### URI identity

Complete `.` and `..` URI path segments are rejected before collision analysis or hashing because RFC 3986 normalization can remove them. The manifest does not silently normalize one declared owner route into another route identity.

### Structural evidence

Before admission or activation, nested generation, route, owner-release, logical-upstream, one-release-per-service, one-owner-per-Path-Item, supported-profile, path identity/matching, operation authority, and canonical configuration-digest invariants are revalidated. Constructor-time success is not durable trust.

Canonically constructed `OwnerApiRelease`, `CompositionRoute`, and `CompositionGeneration` values retain process-local construction identity for the semantic coordinates they were created to represent. A valid-looking low-level retarget of an already-constructed owner release or route is rejected even when every replacement field would be valid on a newly constructed value. New legitimate release or route semantics require a new value object. These snapshots are process-local integrity evidence only; they do not prove release existence, deployment identity, or historical non-reassignment across GC/process restart.

A process-local `AdmissionReceipt` proves only that the canonical evaluator admitted one exact structural state in that process. Directly constructed, reconstructed, serialized/deserialized, post-issuance-mutated, or stale receipt-shaped data does not authorize activation, routing, HR access, or readiness. Durable activation/recovery independently re-evaluates immutable generation and owner evidence.

Actual release existence and owner operation compatibility are not proven by a release-shaped caller value. Production admission requires immutable owner release evidence and operation-level conformance to the referenced OpenAPI/behavior contract.

## Authentication, identity projection, and authorization

Keyverse remains identity/issuer authority. Keyverse #155 owns durable subject-trust semantics and #158 the immutable relying-party release envelope. Orgmetra #295/#297 own durable subject-to-Person binding/consumer ACL. Orgmetra #65 and domain owners retain purpose/resource authorization.

The composition application may map a verified `sub` only to a namespaced opaque runtime actor reference through versioned Orgmetra ACL evidence. `org`/`workspace` are explicitly mapped rather than cast into `tenant_record_id`. Only admitted scope semantics become coarse operation capabilities. Business purpose remains downstream authorization input and never self-authorizes. Contradictory caller-controlled identity/purpose coordinates fail closed.

## Idempotency, retries, cancellation, and concurrency

The composition application forwards canonical owner-required idempotency and optimistic-concurrency coordinates unchanged. It owns no replay fact or product-local version counter. Automatic retry is deny-by-default and is allowed only when the exact released owner operation contract makes the attempted replay safe under observed request state. An ambiguous post-commit transport failure is never converted into a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, and connection loss remain distinguishable evidence.

## Error and scientific-state preservation

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence never become success. RFC 9457 is preferred where an owner publishes Problem Details; composition does not silently rewrite another released owner error contract.

Client-visible failures exclude credentials, restricted HR payloads, stack traces, internal topology, and raw internal trace identifiers.

## Operability, readiness, and recovery

Edge liveness, composition liveness, configuration validity, generation/activation validity, identity-contract admission, per-owner route admission, and buyer product readiness are separate signals. A route-admission receipt is not buyer-readiness evidence.

Activation is generation-atomic. Rollback reactivates a previously admitted immutable generation only after durable generation/configuration/deployment identity and selected owner compatibility are revalidated. Stale process-local receipts are not rollback authority.

Success, rejection, cancellation, timeout, partial response, and owner-unavailable paths release request tasks, buffers, upstream/client connections, and temporary state. When a shared edge is deployed, edge and composition drain semantics are tested together.

## Performance evidence

Applicable commercial paths measure the complete asynchronous deployment:

`client/k6 -> [shared edge if deployed] -> Orgmetra composition -> owner HTTP -> PostgreSQL -> owner -> composition -> [edge] -> client`

For paths designated applicable to the commercial target, p95 must be <= 20 ms. Evidence separates edge, composition, and owner costs. An in-memory router, mocked owner, reduced sample, discarded slow request, disabled auth/audit, skipped database, or warm-cache-only subset cannot establish the SLO.

## Security and privacy invariants

- no cross-service SQL or shared HR write repository;
- no mutable sibling source/config, floating image/tag, or copied owner schema;
- no bearer credential, restricted HR payload, tenant/person identifier, or other high-cardinality sensitive value as an unbounded metric label;
- no caller-controlled identity/purpose coordinate overriding authenticated/projected evidence;
- no owner release whose service identity disagrees with the logical upstream;
- no two exact releases for one owner `service_id` in one generation;
- no one exact OpenAPI Path Item split across owner releases without a future explicit released merge/conformance contract;
- no post-construction owner-release or route retarget accepted as fresh evidence merely because the replacement coordinates are individually valid;
- no post-construction generation identity/configuration rewrite accepted as the same generation;
- no reconstructed or mutated admission receipt treated as durable proof;
- no same-hierarchy path aliases with different template names;
- no cross-owner concrete/template overlap or framework-dependent ambiguous templated overlap;
- no split GET/HEAD selected-resource authority across owners;
- no complete `.` or `..` path segment as distinct route authority;
- no repeated template expression in one route path;
- no claim of full OpenAPI grammar/method support from the bounded #434 profile;
- browser CORS/CSRF/cookie/session behavior explicit when used; and
- every composition/config/deployment change attributable and auditable.

## RED -> GREEN acceptance

Implementation preserves executable RED cases for unsupported or ambiguous route material, cross-owner exact Path Item splits, release/upstream disagreement, split owner-release identities, valid-to-valid post-construction owner/route retargeting, configuration/generation rewrite, forged/stale receipt evidence, path identity/matching/operation collisions, identity/ACL bypass, cross-service SQL, owner semantic distortion, recovery leaks, and benchmarks that bypass deployed layers.

The Path Item RED remains explicit: one exact path cannot be divided across different owner releases merely because the operations use disjoint methods. Exact #434 sequence `ede0b6d602d2160af6c3ae37253f9728ac4b1e08 -> 8b7b059d60bf732e1acc33dc63db2ad8d5cbb52a -> 9852fe6bf1b4cddf1b4710d2908cb42019a0ac86` binds the regression, causal production fix, and documentation without claiming that OpenAPI itself assigns Orgmetra ownership.

The process-local construction-integrity repair is now source-current. Owner-release sequence `0637353074d19327940b72821d497ffba131c284 -> 747c2a7a105e3abf23f8ddfbcb5b662f17e61924 -> 6744a55e95073b2c3f8572c62b84e555f580146a` rejects valid-to-valid low-level owner-release retargeting while preserving newly constructed successor releases. Route sequence `5935135daf9eb2a89bcfd32e32105d9bd9563f96 -> 946d0a25faf5759233fb0aabeaf61f2fac653740 -> 9ced14ae97f8c07285cdc3975f57a81c717313a2` applies the same boundary to route ID, path, method set, required status, and paired owner/upstream semantics. Both remain process-local integrity controls, not durable release or activation provenance.

The previous standards-profile RED remains explicit: documentation must not present the canary as general OpenAPI 3.2 support while executable admission rejects OAS-valid route forms by product policy. Exact #434 sequence `7a30ccd000c5e7b5a69e6f872277e7cf8fab2437 -> a1b903cabc900b33ac4da36f3781bddc50cf57ee` binds that distinction without widening production admission.

Positive controls remain explicit: distinct methods may share the same exact admitted template string **within one exact owner release**, one exact owner release may use concrete-before-template precedence when both routes declare the same method set, and genuinely different owner/route semantics remain legal when represented by newly constructed values.

GREEN requires deployable boundaries, immutable identities for every admitted layer and generation, released owner operation conformance, real/right-cleared evidence where acceptance depends on data, exact current-head tests, supported Podman/Colima and Kubernetes evidence, fault/recovery rehearsal, security evidence, and the applicable full-path latency target.

Exact #434 `9ced14ae...` currently has no PR-triggered hosted workflow evidence. Earlier local coverage figures at predecessor `cb32ba828...` do not transfer. #434 remains Draft and stacked on #340; source history alone is not merge or release authority.

## Implementation and release order

1. Keep #432 as executable product-composition gap owner and #433 Proposed until normal architecture admission.
2. Resolve #340 through its owner lane before treating stacked #434 as protected truth.
3. Shared-edge and Keyverse/Orgmetra identity owners publish immutable contracts Orgmetra actually consumes.
4. Advance #434 ordinary-forward from current protected truth without force/destructive rebase.
5. Implement deployable HTTP composition, runtime-principal projection, durable generation/config/deployment activation, released owner operation conformance, recovery/security evidence, and full-path k6/E2E.
6. #51 reconciles protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and reseals `manifest.json` only after architecture admission.
7. #100 changes durable gap state only when buyer/scientific truth actually changes.
8. Protected integration then immutable Orgmetra release; no release is inferred from an open PR or synthetic fixture.

## Consequences

Generic transport remains reusable without acquiring product semantics. “Thin Orgmetra composition” means a small deployable application contract, not merely a configuration document. The buyer-visible Gateway cannot be claimed shipped until product composition, identity/ACL, required owner APIs, optional edge transport, immutable generation/deployment provenance, recovery, and full-path performance evidence converge on protected/released truth.

The bounded OpenAPI profile reduces unsupported surface now but creates an explicit future compatibility task: if a released Orgmetra owner needs OAS-valid forms outside the current dialect or cross-owner composition under one Path Item, support must expand deliberately with conformance, security, shared-field reconciliation, and path-authority evidence rather than by permissive parser drift.

## References

The focused APA 7th standards/research record is `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in `docs/traceability/gateway-composition-boundary.md` rather than being presented as an external normative standard.
