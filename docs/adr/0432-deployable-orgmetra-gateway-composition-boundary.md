# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, or Orgmetra release production-authoritative. Protected `develop` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. It assigns that buyer-visible boundary API aggregation, tenant context, purpose-bound authorization, idempotency, and event-envelope handling. Protected `docs/API_CONTRACT.md` also places Keyverse OpenID Connect verification ahead of generated request validation. The protected executable repository still does not provide one supported deployable product-composition application across independently versioned owner services.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture/FJA/KSAO, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their existing owners. Product composition is an application adapter. It may consume released identity contracts, project a product principal, select admitted owner operations, correlate requests, preserve transport semantics, and expose composition readiness. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Current owner evidence does not make that repository an Orgmetra composition engine:

- protected `pingora-gateway/main` has no published immutable GitHub Release;
- its generic v1 contract requires one upstream and excludes product route tables, credentials, retry counts, and product authentication/authorization semantics;
- its pg-erd multi-route path is a bounded migration composition whose own authority says it is not a generic product-policy language; and
- Keyverse identity, Orgmetra tenancy/business policy, and HR application semantics remain outside the reusable edge owner.

Therefore a released shared edge may provide transport, but Orgmetra still needs a separately deployable product-composition application.

Draft #434 is the first executable canary under #432. It proves only a route-admission and structural generation-integrity slice. It deliberately does not claim Keyverse authentication, HR authorization, HTTP proxying, durable activation, Kubernetes deployment, buyer-path latency, protected integration, or release completion.

## Decision drivers

The supported boundary must preserve HR bounded-context ownership, consume only immutable released owner contracts, keep Keyverse as identity authority, preserve downstream owner authorization and replay/concurrency/error semantics, prohibit cross-service SQL and mutable sibling dependencies, provide supportable local/Kubernetes deployment and recovery, fail closed when any identity/route/release/configuration/deployment coordinate is unverifiable, expose exact provenance, and measure the complete deployed buyer path.

## Alternatives

### A. Orgmetra-owned gateway also owns generic edge runtime

Rejected as the default. Product composition belongs in Orgmetra, but duplicating reusable TLS/connection/proxy/drain mechanics creates another transport and supplier-security surface.

### B. Shared edge runtime plus configuration only

Rejected for current owner contracts. The current generic edge contract is single-upstream and explicitly excludes the multi-owner product-routing semantics Orgmetra needs. Reusing mutable pg-erd migration routing would move product semantics into the wrong owner.

This option may be revisited only if the shared-edge owner publishes a domain-neutral, release-qualified multi-route capability without absorbing product authentication, tenancy/business policy, or HR authority.

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

The contract binds at least:

- Orgmetra product release/source identity;
- composition application release/artifact digest;
- composition schema version and digest derived from canonical semantic route material;
- immutable generation and activation identity;
- shared-edge release/artifact digest when present;
- released Keyverse consumer-contract identity;
- every admitted owner API/OpenAPI/release identity; and
- environment/deployment identity containing no credential or person/tenant PII.

A Git commit may be provenance but does not replace an immutable consumer/deployment release. A caller-provided digest that is not reproducibly derived from admitted semantic material is not configuration authority.

One canonically constructed generation cannot be rewritten into another semantic generation. `generation_id`, schema identity, and canonical configuration digest remain bound to one lineage. The current Python canary enforces only process-local structural integrity; production activation/rollback requires durable immutable generation/configuration/deployment evidence and historical no-reassignment.

### Route admission

Each admitted route carries a stable `route_id`, exact OpenAPI path template and declared method set, owning service/bounded-context identity, released owner API/OpenAPI/artifact/release coordinates, owner-bound logical upstream, coarse product capability, authoritative tenant/actor/purpose input locations, and required/optional readiness criticality.

All routes for one owner `service_id` in one generation reference one exact `OwnerApiRelease`. The observed owner snapshot is keyed by `service_id`; simultaneous versions of one service require a future version-qualified upstream identity rather than ambiguity in the current key.

The manifest does not mint local retry, idempotency, concurrency, or error-preservation classifications. Those remain released owner truth.

Admission is deny-by-default. Reachability is not admission. Invalid route material fails before configuration identity is minted.

#### OpenAPI path identity

OpenAPI Specification 3.2.1 Section 4.8.1 defines templated paths with the same hierarchy but different template names as identical and says they MUST NOT coexist. Consequently:

- `/v1/people/{person_record_id}` and `/v1/people/{worker_record_id}` are the same OpenAPI path identity even if their HTTP methods are disjoint;
- one path hierarchy maps to one exact template string in one composition generation; and
- distinct HTTP methods may coexist only under the same exact path template, subject to the separate operation-authority rules below.

This path-key identity check runs before effective-method collision analysis and before configuration hashing. Placeholder renaming is not a way to create another path owner.

OpenAPI path-template-expression validity is separate again: one path cannot repeat the same template expression, so `/v1/tenants/{record_id}/people/{record_id}` fails before hashing/admission.

#### HTTP operation authority

After path identity is valid, operation ownership is checked independently. Path templates that can select the same concrete request must not split one effective method authority across different owners. For collision ownership, `GET` and `HEAD` form one selected-resource authority because RFC 9110 Section 9.3.2 defines HEAD as GET semantics without response content. Canonical route material still preserves the methods actually declared; this rule does not synthesize an undeclared HEAD operation.

#### URI identity

Complete `.` and `..` URI path segments are rejected before collision analysis or hashing because RFC 3986 normalization can remove them. The manifest does not silently normalize one declared owner route into another route identity.

### Structural evidence

Before admission or activation, nested generation, route, owner-release, logical-upstream, one-release-per-service, path identity, operation authority, and canonical configuration-digest invariants are revalidated. Constructor-time success is not durable trust.

A process-local `AdmissionReceipt` proves only that the canonical evaluator admitted one exact structural state in that process. Its issued fields remain bound to the issued object. Directly constructed, reconstructed, serialized/deserialized, post-issuance-mutated, or stale receipt-shaped data does not authorize activation, routing, HR access, or readiness. Durable activation/recovery independently re-evaluates immutable generation and owner evidence.

## Authentication, identity projection, and authorization

Keyverse remains identity/issuer authority. Keyverse #155 owns durable subject-trust semantics and #158 the broader immutable relying-party release envelope. Orgmetra #295/#297 own durable subject-to-Person binding/consumer ACL. Orgmetra #65 and domain owners retain purpose/resource authorization.

The composition application may map a verified `sub` only to a namespaced opaque runtime actor reference through versioned Orgmetra ACL evidence. `org`/`workspace` are explicitly mapped rather than cast into `tenant_record_id`. Only admitted scope semantics become coarse operation capabilities. Business purpose remains downstream authorization input and never self-authorizes. Contradictory caller-controlled identity/purpose coordinates fail closed.

## Idempotency, retries, cancellation, and concurrency

The composition application forwards the canonical owner-required `Idempotency-Key` and optimistic-concurrency coordinates unchanged. It owns no replay fact or product-local version counter. Automatic retry is deny-by-default and is allowed only when the exact released owner operation contract makes the attempted replay safe under the observed request state. An ambiguous post-commit transport failure is never converted into a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, and connection loss remain distinguishable evidence.

## Error and scientific-state preservation

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence never become success. RFC 9457 is preferred where an owner publishes Problem Details; the composition layer does not silently rewrite another released owner error contract.

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
- no post-construction generation identity/configuration rewrite accepted as the same generation;
- no reconstructed or mutated admission receipt treated as durable proof;
- no same-hierarchy OpenAPI path aliases with different template names, regardless of HTTP method;
- no split GET/HEAD selected-resource authority across owners;
- no complete `.` or `..` URI path segment as distinct route authority;
- no repeated OpenAPI template expression in one route path;
- browser CORS/CSRF/cookie/session behavior explicit when used; and
- every composition/config/deployment change attributable and auditable.

## RED -> GREEN acceptance

Implementation preserves executable RED cases for at least:

- architecture advertises a Gateway but no deployable composition application exists;
- a shared-edge contract cannot express the Orgmetra product topology;
- a pg-erd migration contract is reused as generic product route authority;
- a route lacks compatible released owner OpenAPI/release evidence;
- config digest is not derived from canonical route material;
- generation identity or route semantics are rewritten after construction;
- one owner service is assigned multiple release identities in one generation;
- logical upstream disagrees with released owner evidence;
- issued receipt fields drift after issuance or stale nested evidence is trusted;
- `GET /v1/people/{person_record_id}` and `PUT /v1/people/{worker_record_id}` coexist even though their templated path hierarchy is identical;
- overlapping routes split one effective method authority, including GET/HEAD selected-resource ownership;
- complete URI dot segments become route authority;
- a path repeats one OpenAPI template expression;
- composition-local replay/idempotency/concurrency semantics diverge from owner truth;
- route admission is represented as buyer readiness;
- unverified Keyverse claims or contradictory identity coordinates reach routing/authorization;
- owner denial/conflict/unavailable/scientific non-success becomes success;
- partially validated or stale configuration activates;
- cancellation/error leaks tasks/connections/buffers;
- composition reaches another context's database; or
- benchmark evidence bypasses a deployed layer or the owner database.

A positive path-identity control also remains explicit: distinct methods such as GET and PUT may share the same exact OpenAPI template string when their operation ownership is otherwise valid. Path-key identity and method-authority collision are different invariants.

GREEN requires deployable boundaries, immutable identities for every admitted layer and generation, real/right-cleared evidence where acceptance depends on data, exact current-head tests, supported Podman/Colima and Kubernetes evidence, fault/recovery rehearsal, security evidence, and the applicable full-path latency target.

Draft #434 currently supplies only the focused admission canary. Current executable authority is `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`, 74 ahead / 0 behind with 13 changed files confined to `services/product-composition-api/**`. Its latest ordinary-forward path-identity sequence is `2b4f2211a2e332058bec31af11474d3937899855` -> `2c7bfcf75ec2d353d52ed86cbcd74dba5ddae3ea` -> `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`. Earlier local coverage figures at predecessor `cb32ba828...` do not transfer to this exact head; no current-head hosted GREEN is claimed merely from source history.

## Implementation and release order

1. Keep #432 as the executable product-composition gap owner and #433 Proposed until normal architecture admission.
2. Resolve #340 through its owner lane before treating stacked #434 as protected truth.
3. Shared-edge and Keyverse/Orgmetra identity owners publish the immutable contracts Orgmetra actually consumes.
4. Advance #434 ordinary-forward from current protected truth, preserving its RED/GREEN evidence without force/destructive rebase.
5. Implement the deployable HTTP composition host, runtime-principal projection, durable generation/config/deployment activation registry, re-admission, and owner-semantic preservation.
6. Obtain supported Podman/Kubernetes, fault/security/recovery, and full-path k6 evidence.
7. Reconcile canonical ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY/baseline through existing single-writer lanes.
8. Normal protected integration precedes version/tag/package/immutable Orgmetra release with SBOM, provenance, reproducibility, and rollback evidence.

## Consequences

Generic transport remains reusable without acquiring product semantics. “Thin Orgmetra composition” means a small deployable application contract, not merely a configuration document. The buyer-visible Gateway cannot be claimed shipped until product composition, identity/ACL, required owner APIs, optional edge transport, immutable generation/deployment provenance, recovery, and full-path performance evidence converge on protected/released truth.

## References

The focused APA 7th standards/research record remains in `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in TRACEABILITY rather than being presented as an external normative standard.
