# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

Verification date: 2026-09-22

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, database registry, deployment, activation, recovery, or Orgmetra release production-authoritative. Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. It assigns that buyer-visible boundary API aggregation and pre-handler identity integration, while protected executable truth still has no supported deployable product-composition application across independently versioned owner APIs.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture/FJA/KSAO, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their existing owners. Product composition is an application adapter. It may consume released identity and authorization contracts, project one product principal, select admitted owner operations, preserve transport and owner semantics, coordinate readiness, and record exact composition activation evidence. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, credentials, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Generic edge transport does not inherit Orgmetra product routing, identity, tenancy, or HR policy authority. Keyverse remains identity/credential authority. Orgmetra identity/ACL and domain owners retain durable subject binding and purpose/resource authorization. Mutable sibling source is not an integration contract.

## Current executable authority

The implementation stack is deliberately split by authority layer:

- #434 exact `68bdf2d984ca7686219c335a85a6574195675cbe`: process-local route/generation admission and construction-integrity canary, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`.
- #436 exact `98b4b129073a2afc70f8a533e34c31fdcc15ab07`: normalized durable generation/configuration registry and canonical reconstruction.
- #437 exact `012c90889ea78db4baa18a2a7973717d00301be1`: durable deployment activation/rollback/recovery, external authorization evidence, owner-operation observations, database-clock freshness, and append-only recovery attestation. It is 84 commits ahead / 0 behind #436 at this verification point.

All three remain Draft/unprotected implementation. Their existence does not close `API-01`, prove a released external dependency, establish buyer readiness, or authorize protected integration.

## Decision

The buyer-visible “Orgmetra Gateway” has two distinct internal responsibilities.

1. **Shared edge transport runtime, externally owned and optional unless a deployment requires it.** It owns connection/proxy/TLS mechanics, bounded transport resources, drain/shutdown, and low-cardinality transport telemetry within its released contract.
2. **Orgmetra product-composition application.** It owns product-facing authentication integration, runtime-principal projection, admitted route selection, owner API compatibility, exact composition generation/deployment state, activation/re-admission coordination, readiness, and end-to-end preservation of downstream semantics.

The Orgmetra component is an application adapter, not an HR bounded context. It owns no HR application table and performs no cross-service SQL. Its durable state is limited to composition configuration, release coordinates, deployment/activation/recovery evidence, and audit/provenance needed to prove which exact composition generation was admitted or active.

## Evidence layers

Evidence layers are intentionally non-interchangeable.

### Process-local structural evidence

`OwnerApiRelease`, `CompositionRoute`, `CompositionGeneration`, `AdmissionReceipt`, `DeploymentIdentity`, `ReleasedAuthorityEvidence`, `OwnerOperationObservation`, and `ActivationAdmissionEvidence` use process-local construction/issuance integrity where applicable. Valid-looking low-level mutation of an already-constructed object into another semantic meaning is rejected. New legitimate semantics require a new value.

These controls are defense in depth. Python object identity, a frozen dataclass, a caller digest, or a receipt-shaped value is not durable release/deployment authority.

### Durable generation/configuration authority

Migration `0018_product_composition_generation_registry.sql` persists normalized generation, owner-release, route, and route-method material. One `generation_id` cannot acquire two semantic meanings. Durable rows must reconstruct fresh canonical values and reproduce the configuration digest; a stored digest alone is insufficient. Generation material is append-only and destructive rewrite/truncation is rejected.

### Durable activation authority

Migration `0019_product_composition_activation_registry.sql` introduces explicit non-PII `(deployment_id, environment_id)` identity, content-addressed external evidence, exact owner-operation observations, and append-only activation events. Activation and rollback serialize on the exact deployment row with `FOR UPDATE`; rollback is a new event targeting previously active immutable generation material rather than mutation of history.

Migration `0020_product_composition_activation_authority_enforcement.sql` refuses predecessor NULL-evidence activation history and makes current activation events evidence-bound. The structural registry remains useful for predecessor-schema/fault tests, but current production schema does not allow evidence-free structural activation history.

### Database-clock observation authority

Migration `0021_product_composition_activation_observation_wall_clock.sql` rejects new owner-operation observations dated after PostgreSQL wall clock or already stale when persisted. It also refuses an upgrade over predecessor future-dated observation history.

The upgrade itself is transactional authority. #437's current repair wraps the predecessor-history scan and permanent INSERT-guard installation in one explicit transaction, acquires `SHARE ROW EXCLUSIVE` on `product_composition_activation_owner_observation` before the scan, and holds that writer-conflicting lock through trigger creation. This closes the scan/install TOCTOU where a predecessor-schema writer could otherwise commit impossible history after preflight but before the guard became effective. `tests/test_product_composition_activation_observation_wall_clock_upgrade_postgres.sh` models that concurrent writer.

### Durable restart re-admission authority

Migration `0022_product_composition_recovery_attestation.sql` persists each successful fresh restart re-admission as append-only recovery-attestation history bound to the exact current activation sequence, generation, and fresh `authorization_action='recover'` evidence. PostgreSQL rechecks recovery action/state binding, evidence expiry, and exact fresh owner-operation coverage before accepting the attestation. UPDATE, DELETE, and TRUNCATE are rejected.

Remote evidence acquisition stays outside the deployment-row lock. Recovery reads current state, obtains fresh external evidence, then reacquires the exact deployment lock. The locked path fails closed unless activation sequence and generation still equal what was externally verified, reconstructs the generation again, persists/verifies the evidence bundle, and appends the recovery attestation in one local transaction. Network I/O is not held under `FOR UPDATE`.

The current composition migration order is therefore **0018 -> 0019 -> 0020 -> 0021 -> 0022**.

## Product-composition contract

The implementation owner introduces a versioned contract equivalent to `orgmetra_gateway_composition.v1`.

A generation binds product/composition release provenance, schema/configuration identity, immutable owner API/OpenAPI/artifact/release coordinates, stable routes and methods, logical upstreams, required/optional readiness status, and deployment/activation coordinates. A Git commit may be provenance but does not replace an immutable consumer/deployment release. A caller-provided digest not reproducibly derived from admitted semantic material is not configuration authority.

### Route admission

Each route carries a stable lower-snake-case `route_id`, exact product path template and declared method set, exact `OwnerApiRelease`, owner-bound logical `service://` upstream, and required/optional status. One owner `service_id` maps to one exact release/OpenAPI/artifact identity per generation.

Protected HTTP contract truth remains OpenAPI 3.2.0. The canary intentionally supports a stricter fail-closed route profile. Expanding it requires a released owner need plus conformance tests; framework acceptance alone is not evidence.

Route identity retains separate layers:

- OpenAPI-equivalent templated paths with the same hierarchy but different placeholder names cannot coexist as separate identities.
- One exact Path Item has one exact owner release in the current product profile.
- Concrete-before-template overlap is admitted only under the same exact owner release and same declared method set.
- Cross-owner concrete/template overlap and ambiguous templated overlap fail closed.
- HTTP operation collision is evaluated only after Path Item ownership and deterministic path matching are valid; GET/HEAD share selected-resource collision authority without synthesizing an undeclared method.
- Complete URI `.` / `..` segments and repeated template expressions are rejected before configuration identity.

Product composition does not invent local retry, idempotency, concurrency, replay, or scientific-state taxonomies. Those remain released owner truth.

## Authentication, identity projection, and authorization

Keyverse remains identity/issuer authority. Orgmetra identity/ACL owners retain durable subject-to-Person binding and consumer ACL. Domain owners retain purpose/resource authorization.

Composition may map a verified subject only to a namespaced opaque runtime actor reference through versioned Orgmetra ACL evidence. Caller-controlled organization/workspace/purpose fields do not override authenticated/projected evidence. Business purpose is propagated as downstream authorization input and never self-authorizes.

Production activation requires immutable released Keyverse/Orgmetra policy coordinates and exact owner-operation evidence. Synthetic release locators/digests are test fixtures only and cannot establish buyer-ready authority.

## Idempotency, retries, cancellation, and concurrency

Composition forwards canonical owner-required idempotency and optimistic-concurrency coordinates unchanged. Automatic retry is deny-by-default unless the exact released owner operation contract proves replay safety for the observed request state. An ambiguous post-commit transport failure never becomes a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, and connection loss remain distinguishable evidence.

## Error and scientific-state preservation

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence never becomes success. Client-visible failures exclude credentials, restricted HR payloads, stack traces, internal topology, and raw internal trace identifiers.

## Operability, readiness, and recovery

Edge liveness, composition liveness, configuration validity, generation/activation validity, identity-contract admission, per-owner route admission, fresh recovery re-admission, and buyer product readiness are separate signals. A process-local admission receipt is not buyer-readiness evidence.

Activation is generation-atomic. Rollback reactivates previously persisted immutable generation material only after current external authority and owner compatibility are re-admitted. Successful recovery survives process exit as a separate durable attestation rather than rewriting the historical activation event.

Success, rejection, cancellation, timeout, partial response, and owner-unavailable paths release request tasks, buffers, upstream/client connections, and temporary state. Shared-edge and composition drain semantics are tested together when both layers are deployed.

## Security and privacy invariants

- no cross-service SQL or shared HR write repository;
- no mutable sibling source/config, floating image/tag, or copied owner schema;
- no bearer credential, restricted HR payload, tenant/person identifier, or other high-cardinality sensitive value as an unbounded metric label;
- no caller-controlled identity/purpose coordinate overriding authenticated/projected evidence;
- no owner release whose service identity disagrees with logical upstream;
- no two exact releases for one owner `service_id` in one generation;
- no exact Path Item split across owner releases without a future released merge/conformance contract;
- no post-construction owner/route/generation/evidence retarget accepted as fresh authority;
- no receipt-shaped value treated as durable activation authority;
- no future-dated or expired owner-operation observation admitted as current evidence;
- no predecessor migration writer allowed to cross the 0021 history-scan/guard-install boundary;
- no evidence-free current-schema activation event;
- no restart recovery claimed without append-only fresh recovery attestation;
- no same-hierarchy path aliases, cross-owner ambiguous overlap, split GET/HEAD authority, URI dot-segment alias, or repeated template expression;
- browser CORS/CSRF/cookie/session behavior explicit when used; and
- every composition/configuration/deployment/recovery change attributable and auditable.

## Performance evidence

Applicable commercial paths measure the complete asynchronous deployment:

`client/k6 -> [shared edge if deployed] -> Orgmetra composition -> owner HTTP -> PostgreSQL -> owner -> composition -> [edge] -> client`

For paths designated applicable to the commercial target, p95 must be <=20 ms. Evidence reports edge, composition, and owner costs separately. An in-memory router, mocked owner, reduced sample, discarded slow request, disabled auth/audit, skipped database, or warm-cache-only subset cannot establish the SLO.

## Verification and integration authority

#433 remains Proposed until independent architecture admission. Its previous exact source head `912fa44ec3b928500acea0291103cb41f6a6d7fc` had terminal Foundation, SAST, Security, and CodeQL success but no submitted review. This source currentization is a material head change, so predecessor GREEN must not be transferred; fresh exact-head evidence is required.

#437 remains stacked on #436 rather than protected `develop`, so its static/Python/PostgreSQL contracts are executable source evidence rather than protected exact-head GREEN. Canonical execution remains owned by #260/#311 after their declared prerequisites. Those owners must not copy mutable #437 source. Once their capability reaches protected truth, the composition stack ordinary-forward adopts it and executes the product-composition service, ordered migrations 0018→0022, concurrent 0021 upgrade contract, recovery-attestation contract, and 100% owned statement/branch coverage from the same exact candidate tree.

#340 remains an inherited Foundation prerequisite and currently has a required CodeQL failure. #259/#311 are also blocked by their normal central gate/review dependencies. No leaf shim, synthetic status, no-op rerun, routine administrator bypass, force-push/destructive rebase, self-approval, or gate weakening is authorized.

## RED -> GREEN acceptance

GREEN requires all of the following on current protected/released truth:

- supported deployable HTTP product composition bound to immutable generation/configuration/deployment identity;
- released Keyverse consumer evidence and released Orgmetra ACL/purpose evidence;
- released owner API/OpenAPI/artifact evidence and exact operation-level conformance;
- fail-closed generation-ID reassignment, partial registry writes, route/release mismatch, invalid activation/rollback/recovery evidence, concurrent state changes, predecessor migration races, stale/future evidence, mutation/truncation attempts, and restart reconstruction;
- exact-head pytest plus 100% owned statement/branch/docstring/edge evidence where tooling exposes it;
- isolated PostgreSQL acceptance through the current ordered migration chain;
- Foundation/SAST/Security/CodeQL plus qualifying independent review;
- supported Podman/Colima and Kubernetes deployment/recovery evidence;
- fault/security/recovery rehearsal; and
- full applicable buyer-path k6/E2E with p95 <=20 ms and no omitted deployed layer.

## Implementation and release order

1. Keep #432 as buyer-visible composition-gap owner and #433 Proposed until normal architecture admission.
2. Resolve #340 and the canonical Foundation prerequisites through their owner lanes.
3. Integrate #260/#311 capabilities to protected truth; composition then ordinary-forward adopts canonical service/PostgreSQL execution without copying mutable sibling source.
4. Preserve #434 process-local admission, #436 durable generation/configuration, and #437 durable activation/recovery as separate evidence layers while reconciling them onto current protected truth.
5. Obtain actual immutable Keyverse/Orgmetra/owner releases and prove positive activation plus restart recovery against those releases.
6. Implement the deployable HTTP composition host and exact owner routing without taking HR domain truth.
7. Acquire security/fault/recovery and complete buyer-path performance evidence.
8. #51 reconciles protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and reseals `manifest.json` after architecture admission.
9. #100 changes durable gap state only when buyer/scientific truth actually changes.
10. Protected integration then immutable Orgmetra release with version/CHANGELOG/tag/package/SBOM/provenance/reproducibility/rollback evidence.

## Consequences

Generic transport remains reusable without acquiring product semantics. “Thin Orgmetra composition” means a small deployable application contract, not merely a configuration document. The buyer-visible Gateway cannot be claimed shipped until product composition, identity/ACL, required owner APIs, optional edge transport, immutable generation/deployment provenance, recovery, and full-path performance evidence converge on protected/released truth.

The bounded OpenAPI profile reduces unsupported surface now but leaves an explicit compatibility path: if a released owner requires valid OpenAPI forms outside the current dialect or cross-owner composition under one Path Item, support expands deliberately with conformance, shared-field reconciliation, security, and path-authority evidence rather than permissive parser drift.

## References

The focused APA 7th standards/research record is `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in `docs/traceability/gateway-composition-boundary.md` rather than being presented as an external normative standard.
