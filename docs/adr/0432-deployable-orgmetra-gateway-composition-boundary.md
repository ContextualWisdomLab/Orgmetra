# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

Verification date: 2026-09-23

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, database registry, deployment, activation, recovery, or Orgmetra release production-authoritative. Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. The buyer-visible boundary needs API aggregation and pre-handler identity integration, but protected executable truth still has no supported deployable product-composition application across independently versioned owner APIs.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture/FJA/KSAO, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their existing owners. Product composition is an application adapter. It may consume released identity and authorization contracts, project one product principal, select admitted owner operations, preserve transport and owner semantics, coordinate readiness, and record exact composition activation evidence. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, credentials, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Generic edge transport does not inherit Orgmetra product routing, identity, tenancy, or HR policy authority. Keyverse remains identity/credential authority. Orgmetra identity/ACL and domain owners retain durable subject binding and purpose/resource authorization. Mutable sibling source is not an integration contract.

## Current executable authority

The implementation stack remains deliberately split by authority layer:

- #434 exact `68bdf2d984ca7686219c335a85a6574195675cbe`: process-local route/generation admission and construction-integrity canary, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`.
- #436 exact `5fd0087179f2e6f23f2bb3853ad1de397fc53b0e`: normalized durable generation/configuration registry, canonical reconstruction, append-only generation material, and caller-search-path-independent 0018 publication.
- #437 exact `960a5fbfcb98075862cdbee8ee094a9b8d7dcc55`: durable deployment activation/rollback/recovery through migration 0025, transition-bound external evidence, PostgreSQL-clock owner-observation validity, durable restart re-admission, migration upgrade fencing, deployment-row serialization, full-chain schema provenance, trusted trigger-function provenance, generation-anchored activation/recovery relation ownership, checked-as-used process-local runtime capability integrity, and a no-ambiguous-post-commit recovery boundary.

All three are Draft/unprotected implementation evidence. Their existence does not close `API-01`, prove a released external dependency, establish buyer readiness, or authorize protected integration.

## Problem and constraints

The product needs a buyer-visible composition boundary that can route independently released owner APIs without copying owner schemas or creating a second HR source of truth. The boundary must survive process restart and deployment change while preserving exact release, configuration, authorization, and recovery provenance.

The design is constrained by the following:

- HR domain truth and ubiquitous language stay in Orgmetra owner bounded contexts;
- Keyverse remains identity/credential authority;
- mutable branches, copied sibling source, and cross-service SQL are not integration contracts;
- remote identity/ACL/owner checks must not hold a local deployment-row lock across network I/O;
- generation, deployment, activation, rollback, and recovery history must be attributable and fail closed under concurrent writers;
- migration publication and migration-time object provenance are part of durable authority;
- direct SQL must not have weaker deployment-state serialization than the product adapter;
- caller-controlled migration `search_path` must not redirect composition authority objects or trigger functions;
- process-local capability snapshots are defense in depth and never substitute for PostgreSQL or immutable released evidence;
- once a recovery transaction has committed, a later local observation must not reclassify that committed success as a failure;
- Draft implementation, source-local tests, or process-local receipts are not protected or released authority; and
- the final buyer path must include every actually deployed edge/composition/owner/PostgreSQL layer and meet the applicable p95 <=20 ms target without benchmark exclusions.

## Decision

The buyer-visible “Orgmetra Gateway” has two distinct internal responsibilities.

1. **Shared edge transport runtime, externally owned and optional unless a deployment requires it.** It owns connection/proxy/TLS mechanics, bounded transport resources, drain/shutdown, and low-cardinality transport telemetry within its released contract.
2. **Orgmetra product-composition application.** It owns product-facing authentication integration, runtime-principal projection, admitted route selection, owner API compatibility, exact composition generation/deployment state, activation/re-admission coordination, readiness, and end-to-end preservation of downstream semantics.

The Orgmetra component is an application adapter, not an HR bounded context. It owns no HR application table and performs no cross-service SQL. Its durable state is limited to composition configuration, release coordinates, deployment/activation/recovery evidence, and the audit/provenance needed to prove which exact composition generation was admitted or active.

## Alternatives considered

### Put product routing and HR truth into one gateway database

Rejected. It creates a second HR bounded context, invites cross-service SQL, and makes product composition authoritative over Person/Organization/Job/Talent/Assessment/Workforce state that belongs to domain owners.

### Use mutable branch/source checkout as the integration contract

Rejected. Mutable source cannot establish immutable owner release identity or deployment provenance and makes exact reconstruction/recovery unverifiable.

### Keep activation/recovery only in process memory

Rejected. A restart would erase the evidence that authorized the active generation and make rollback/recovery lineage non-auditable.

### Let migration runners publish tables first and install guards later

Rejected. PostgreSQL DDL is transactional, but an autocommit migration sequence can expose a newly committed relation before later trigger statements. Rows written during that gap are not retroactively validated by triggers. Schema publication must therefore be atomic wherever guards define durable authority.

### Rely on migration-session `search_path` for authority object identity

Rejected. A caller-controlled schema can shadow or receive unqualified objects/functions. Composition authority relations, foreign-key targets, trigger targets, and trigger functions must resolve to the reviewed `public` objects independently of the caller's path.

### Serialize only application-adapter writers

Rejected. Direct SQL activation and recovery would then observe weaker authority than product traffic. Both direct writer paths must acquire the same deployment-row lock before lineage/evidence validation.

### Treat the activation child tables as their own ownership trust root

Rejected. A uniform foreign transfer of every child relation could otherwise look internally consistent. The parent `product_composition_generation` relation is the ownership anchor for deployment/evidence/observation/event/recovery relations.

### Hold remote verification under `FOR UPDATE`

Rejected. It converts external latency/failure into a long database lock and widens contention. Remote evidence is acquired first, then exact deployment state is locked and revalidated before local persistence.

### Revalidate local wall-clock freshness after recovery commit

Rejected. `recover_active_authorized()` commits before returning. A second fallible local freshness check after that return can tell the caller “failure” after a durable recovery attestation already exists. Local freshness is checked before persistence; PostgreSQL is the commit-time freshness authority.

## Evidence layers

Evidence layers are intentionally non-interchangeable.

### Process-local structural evidence

`OwnerApiRelease`, `CompositionRoute`, `CompositionGeneration`, `AdmissionReceipt`, `DeploymentIdentity`, `ReleasedAuthorityEvidence`, `OwnerOperationObservation`, and `ActivationAdmissionEvidence` use process-local construction/issuance integrity where applicable. Valid-looking low-level mutation of an already-constructed object into another semantic meaning is rejected; new legitimate semantics require a new value.

The package-root `AuthorizedPostgresActivationRegistry` also binds the admitted evidence provider, validation clock, generation registry, structural activation registry, and their PostgreSQL connection factories to a construction snapshot. It checks that capability identity before durable reads and around the external callback. This protects checked-as-used local capability meaning, but remains process-local defense in depth.

Python object identity, a frozen dataclass, a caller digest, or a receipt-shaped value is not durable release/deployment authority.

### Durable generation/configuration authority — 0018

Migration `0018_product_composition_generation_registry.sql` persists normalized generation, owner-release, route, and route-method material. One `generation_id` cannot acquire two semantic meanings. Durable rows reconstruct fresh canonical values and reproduce the configuration digest; a stored digest alone is insufficient. Generation material is append-only and destructive rewrite/truncation is rejected.

0018 publishes the generation registry and its mutation guards atomically. It also pins object publication to trusted `public` rather than trusting caller `search_path`. #436 exact `5fd0087179f2e6f23f2bb3853ad1de397fc53b0e` is the current Draft implementation authority for this layer.

### Durable activation/recovery authority — 0019 through 0025

The ordered composition migration chain is **0018 -> 0019 -> 0020 -> 0021 -> 0022 -> 0023 -> 0024 -> 0025**.

- **0019** introduces non-PII `(deployment_id, environment_id)` identity, content-addressed external evidence, exact owner-operation observations, and append-only activation events. Its relation/function/trigger publication is one transaction and explicitly targets `public`.
- **0020** refuses predecessor NULL-evidence activation history and makes current activation events evidence-bound. The authority upgrade is transactionally fenced so a predecessor writer cannot cross the preflight/constraint-promotion boundary.
- **0021** rejects future-dated or already-stale owner-operation observations against PostgreSQL wall clock, refuses grandfathered impossible predecessor history, and fences predecessor writers across the history scan and guard installation.
- **0022** persists each successful restart re-admission as append-only recovery-attestation history bound to the exact current activation sequence, generation, and fresh `authorization_action='recover'` evidence. Its table and guards publish atomically.
- **0023** makes direct activation and recovery writers acquire the same `product_composition_deployment` row lock before existing lineage/evidence triggers run. Product and direct-SQL writer serialization therefore share one database authority.
- **0024** verifies the critical public trigger functions and rebinds all 16 activation/recovery INSERT, append-only, and TRUNCATE triggers to explicit `public.<function>()` identities. Trigger-function provenance is independent of migration-session `search_path`.
- **0025** locks the parent generation authority plus all five activation/recovery relations and requires every child relation owner to match the owner of `public.product_composition_generation`. It rejects both split ownership and a uniform foreign transfer without silently repairing ownership with `ALTER OWNER`.

The full-chain hostile-search-path contract executes 0018→0025 from a caller-controlled schema and requires all nine composition authority relations to remain in `public`, no authority relation/function to appear in the decoy schema, and all 16 activation/recovery triggers to bind trusted public functions.

### Transition and recovery evidence

Remote evidence acquisition stays outside the deployment-row lock. Activation/rollback obtains external evidence first, then the structural path locks the deployment, compares the exact prior sequence, reconstructs durable generation material, persists/verifies the evidence bundle, and appends the transition.

Recovery first reads the active durable event/generation and requires historical activation evidence, obtains fresh `recover` evidence outside the lock, then locks the deployment and requires the activation sequence and generation to remain exactly what was externally verified. It reconstructs the generation again, persists/verifies fresh evidence, and appends the next recovery attestation in the same local transaction.

Fresh recovery evidence is validated against the admitted local clock before the commit-capable call. PostgreSQL independently applies database-clock freshness while inserting evidence and the attestation. Once `recover_active_authorized()` returns, the durable transaction is committed; the product wrapper does not perform another fallible local-clock or capability decision that could report a false failure after that commit. A later request may fail closed if runtime capability integrity has been lost, but the committed attestation is not retrospectively reclassified.

## Product-composition contract

The implementation owner introduces a versioned contract equivalent to `orgmetra_gateway_composition.v1`.

A generation binds product/composition release provenance, schema/configuration identity, immutable owner API/OpenAPI/artifact/release coordinates, stable routes and methods, logical upstreams, required/optional readiness status, and deployment/activation coordinates. A Git commit may be provenance but does not replace an immutable consumer/deployment release. A caller-provided digest not reproducibly derived from admitted semantic material is not configuration authority.

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

## Idempotency, retries, cancellation, errors, and scientific state

Composition forwards canonical owner-required idempotency and optimistic-concurrency coordinates unchanged. Automatic retry is deny-by-default unless the exact released owner operation contract proves replay safety for the observed request state. An ambiguous post-commit transport failure never becomes a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, and connection loss remain distinguishable evidence.

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence never becomes success. Client-visible failures exclude credentials, restricted HR payloads, stack traces, internal topology, and raw internal trace identifiers.

## Operability and readiness

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
- no post-construction owner/route/generation/evidence/runtime-capability retarget accepted as fresh authority;
- no receipt-shaped value treated as durable activation authority;
- no future-dated or expired owner-operation observation admitted as current evidence;
- no generation/activation/recovery authority relation externally visible before guards defining its durable invariants are installed;
- no caller-controlled migration path redirecting composition authority relations/functions;
- no direct-SQL activation/recovery writer bypassing shared deployment-row serialization;
- no activation/recovery trigger resolving through an untrusted function identity;
- no child activation/recovery relation owner diverging from parent generation authority at provenance admission;
- no evidence-free current-schema activation event;
- no restart recovery claimed without append-only fresh recovery attestation;
- no post-commit local observation reclassifying a committed recovery as failed;
- no concurrency regression that relies only on arbitrary scheduler sleep to prove hostile interleaving;
- no same-hierarchy path aliases, cross-owner ambiguous overlap, split GET/HEAD authority, URI dot-segment alias, or repeated template expression;
- browser CORS/CSRF/cookie/session behavior explicit when used; and
- every composition/configuration/deployment/recovery change attributable and auditable.

## Performance evidence

Applicable commercial paths measure the complete asynchronous deployment:

`client/k6 -> [shared edge if deployed] -> Orgmetra composition -> owner HTTP -> PostgreSQL -> owner -> composition -> [edge] -> client`

For paths designated applicable to the commercial target, p95 must be <=20 ms. Evidence reports edge, composition, and owner costs separately. An in-memory router, mocked owner, reduced sample, discarded slow request, disabled auth/audit, skipped database, or warm-cache-only subset cannot establish the SLO.

## Risks and effects

The durable-authority design adds schema, lock, migration, test, and operational surface. This is accepted because configuration, activation, recovery, and external authorization need different lifecycles and must remain reconstructable after process exit.

Migration-level provenance checks do not themselves prove least-privilege production database-role deployment. Runtime/migrator role separation and privileges remain deployment evidence and must be demonstrated before release. A superuser or object owner can defeat ordinary DDL/DML guards; the production role model therefore cannot be inferred merely from successful migration tests.

Writer-conflicting migration fences can block or be blocked by active transactions. Upgrade rehearsal must measure lock acquisition, timeout/abort behavior, rollback, and retry on supported PostgreSQL deployment paths.

The bounded OpenAPI profile may reject valid future owner forms. Expansion is deliberate: a released owner need, compatibility contract, tests, and architecture review must precede a wider dialect.

## Verification and integration authority

#433 remains Proposed until independent architecture admission. This source currentization moves architecture evidence to current #436 `5fd0087179f2e6f23f2bb3853ad1de397fc53b0e` and #437 `960a5fbfcb98075862cdbee8ee094a9b8d7dcc55`; predecessor checks/reviews do not transfer to the resulting #433 head.

#436/#437 remain stacked Draft candidates rather than protected `develop`. Their Python/static/PostgreSQL contracts are executable source evidence rather than protected exact-head GREEN. Canonical execution remains owned by #260/#311 after their declared prerequisites. Those owners must not copy mutable composition source. Once their capability reaches protected truth, the composition stack ordinary-forward adopts it and executes the product-composition service, ordered migrations 0018→0025, hostile generation/full-chain search-path contracts, 0020/0021 upgrade-race contracts, recovery-attestation and deployment-serialization contracts, trigger/relation-provenance contracts, runtime-capability integrity, the recovery commit-boundary regression, and 100% owned statement/branch/docstring/edge coverage from one exact candidate tree.

#340 remains an inherited Foundation prerequisite. No leaf shim, synthetic status, no-op rerun, routine administrator bypass, force-push/destructive rebase, self-approval, or gate weakening is authorized.

`API-01` remains Planned under #100 because no protected deployable buyer path exists.

## RED -> GREEN acceptance

GREEN requires all of the following on current protected/released truth:

- supported deployable HTTP product composition bound to immutable generation/configuration/deployment identity;
- released Keyverse consumer evidence and released Orgmetra ACL/purpose evidence;
- released owner API/OpenAPI/artifact evidence and exact operation-level conformance;
- fail-closed generation-ID reassignment, partial registry writes, route/release mismatch, invalid activation/rollback/recovery evidence, concurrent state changes, migration publication/provenance races, stale/future evidence, mutation/truncation attempts, runtime-capability retarget, and restart reconstruction;
- exact-head pytest plus 100% owned statement/branch/docstring/edge evidence where tooling exposes it;
- isolated PostgreSQL acceptance through ordered migrations 0018→0025;
- Foundation/SAST/Security/CodeQL plus qualifying independent review;
- supported Podman/Colima and Kubernetes deployment/recovery evidence;
- fault/security/recovery rehearsal; and
- full applicable buyer-path k6/E2E with p95 <=20 ms and no omitted deployed layer.

## Implementation and release order

1. Keep #432 as buyer-visible composition-gap owner and #433 Proposed until normal architecture admission.
2. Currentize the architecture-owner TRACEABILITY on the same exact #436/#437 evidence, then reacquire #433 exact-head checks and independent review.
3. Resolve #340 and canonical Foundation prerequisites through their owner lanes.
4. Integrate #260/#311 capabilities to protected truth; composition then ordinary-forward adopts canonical service/PostgreSQL execution without copying mutable sibling source.
5. Preserve #434 process-local admission, #436 durable generation/configuration, and #437 durable activation/recovery as separate evidence layers while reconciling them onto current protected truth.
6. Obtain actual immutable Keyverse/Orgmetra/owner releases and prove positive activation plus restart recovery against those releases.
7. Implement the deployable HTTP composition host and exact owner routing without taking HR domain truth.
8. Acquire security/fault/recovery and complete buyer-path performance evidence.
9. #51 reconciles protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and reseals `manifest.json` after architecture admission.
10. #100 changes durable gap state only when buyer/scientific truth actually changes.
11. Protected integration then immutable Orgmetra release with version/CHANGELOG/tag/package/SBOM/provenance/reproducibility/rollback evidence.

## Consequences

Generic transport remains reusable without acquiring product semantics. “Thin Orgmetra composition” means a small deployable application contract, not merely a configuration document. The buyer-visible Gateway cannot be claimed shipped until product composition, identity/ACL, required owner APIs, optional edge transport, immutable generation/deployment provenance, recovery, and full-path performance evidence converge on protected/released truth.

The bounded OpenAPI profile reduces unsupported surface now but leaves an explicit compatibility path: if a released owner requires valid OpenAPI forms outside the current dialect or cross-owner composition under one Path Item, support expands deliberately with conformance, shared-field reconciliation, security, and path-authority evidence rather than permissive parser drift.

## Follow-up

- Keep `docs/traceability/gateway-composition-boundary.md` on the same exact executable stack and evidence distinctions.
- Require #260/#311 canonical execution to discover the product-composition service and ordered PostgreSQL roots from the same candidate tree.
- Re-run exact-head architecture checks after every material ADR/TRACEABILITY change; do not transfer predecessor GREEN.
- Require independent architecture review before changing Status from Proposed.
- Prove production database-role least privilege separately from migration trigger/owner provenance.
- Change buyer-visible gap truth only through #100 after protected deployable evidence exists.

## References

The focused APA 7th standards/research record is `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in `docs/traceability/gateway-composition-boundary.md` rather than being presented as an external normative standard.
