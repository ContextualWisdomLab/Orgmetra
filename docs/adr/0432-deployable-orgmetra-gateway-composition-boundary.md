# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

Verification date: 2026-09-24

This ADR is design authority only. It does not make a gateway, shared edge runtime, product-composition service, owner API, database registry, deployment, activation, recovery, or Orgmetra release production-authoritative. Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` remains shipped truth until normal review, exact-head checks, protected integration, and immutable release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between role workspaces and independently owned domain services. The buyer-visible boundary needs API aggregation and pre-handler identity integration, but protected executable truth still has no supported deployable product-composition application across independently versioned owner APIs.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture/FJA/KSAO, Talent, Performance, Assessment coordination, Workforce Validation, document, integration, and audit truth remain with their existing owners. Product composition is an application adapter. It may consume released identity and authorization contracts, project one product principal, select admitted owner operations, preserve transport and owner semantics, coordinate readiness, and record exact composition activation evidence. It must not become a second source of HR truth, purpose policy, idempotency truth, concurrency truth, retry safety, credentials, or scientific evidence.

CWL also has a reusable edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Generic edge transport does not inherit Orgmetra product routing, identity, tenancy, or HR policy authority. Keyverse remains identity/credential authority. Orgmetra identity/ACL and domain owners retain durable subject binding and purpose/resource authorization. Mutable sibling source is not an integration contract.

## Current executable authority

The implementation stack remains deliberately split by authority layer:

- #434 exact `68bdf2d984ca7686219c335a85a6574195675cbe`: process-local route/generation admission and construction-integrity canary, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`.
- #436 exact `30d89fa8f4ba95d7ddb84dde8e3b7e5faebf0343`: normalized durable generation/configuration registry, canonical reconstruction, append-only generation material, and caller-search-path-independent 0018 publication.
- #437 exact `a09d6fb928e0272673b82ef7353ed83213aa994d`: durable deployment activation/rollback/recovery through migration 0025 plus request-time serving currentness. Expected otherwise-valid recovery-evidence expiry is `ServingEvidenceExpiredError`, an `ActivationConflictError`; clock rewind, malformed/retargeted durable state and other integrity/authorization failures remain `ActivationAuthorizationError`.
- #438 exact `6cd7a9081696c29fd3ce43a9f776fccfbf9ecaab`: declared Path Item/method selection before PostgreSQL currentness, stable `route_id` projection, and fail-closed concrete-before-template request routing.
- #439 exact `dbee7dcd6ce641e23fe93dcc59b643c066eed526`: raw ASGI request-target evidence. `raw_path` and decoded path identity are checked before route selection so percent-encoded, fragment, non-ASCII, dot-segment, and malformed transport aliases do not become a different route identity.
- #440 exact `0050f14701ea92fd85a2691a280d29c46a97b63b`: HTTP method/error projection, current request-time `Allow`, GET-backed HEAD authority, HEAD no-content error emission, and RFC 9457 problem serialization.
- #442 exact `9bbb792ef43fca8b08684f4f55a8bfe65e1120da`: typed durable-currentness projection. Only `ActivationConflictError` becomes route unavailability; `ActivationAuthorizationError` remains an integrity/security failure and is not laundered into ordinary 503 serviceability.
- #443 exact `728f07a8c86f92bbf33586f2a8007da9f31f5e06`: bounded inbound ASGI body/receive lifecycle with independent byte and receive-event budgets, malformed-event rejection, distinct `http.disconnect`, and explicit capability-shape versus server/runtime-failure ownership.
- #444 exact `e1af671deeeec682dffdf809cb8579dcc4d439da`: outbound core HTTP response-event/send lifecycle. Core response direction/schema, valid status 100..599, lowercase RFC 9110 token field names, invalid field-control rejection, trailer fail-closed behavior, callable/awaitable send shape, and server-side failure propagation remain separate.
- #446 exact `7954f5bf606584ddb5bbcd29e1b64e49041b9409`: complete non-streaming ASGI response prevalidation before irreversible `http.response.start`, terminal completion, HEAD/204/205/304 no-content handling, `Content-Length` consistency, protocol-server ownership of outbound transfer coding, detachment of caller-owned mutable header pairs, and the current review-quality repair.

All of these are Draft/unprotected implementation evidence. Their existence does not close `API-01`, prove a released external dependency, establish buyer readiness, or authorize protected integration. #440/#442/#443/#444/#446 add no SQL; the composition PostgreSQL lineage remains **0018 -> 0025**.

## Problem and constraints

The product needs a buyer-visible composition boundary that can route independently released owner APIs without copying owner schemas or creating a second HR source of truth. The boundary must survive process restart and deployment change while preserving exact release, configuration, authorization, recovery, request-currentness, and transport provenance.

The design is constrained by the following:

- HR domain truth and ubiquitous language stay in Orgmetra owner bounded contexts;
- Keyverse remains identity/credential authority;
- mutable branches, copied sibling source, and cross-service SQL are not integration contracts;
- remote identity/ACL/owner checks must not hold a local deployment-row lock across network I/O;
- generation, deployment, activation, rollback, recovery, and request-time currentness must be attributable and fail closed under concurrent writers;
- migration publication and migration-time object provenance are part of durable authority;
- direct SQL must not have weaker deployment-state serialization than the product adapter;
- caller-controlled migration `search_path` must not redirect composition authority objects or trigger functions;
- process-local capability snapshots are defense in depth and never substitute for PostgreSQL or immutable released evidence;
- once a recovery transaction has committed, a later local observation must not reclassify that committed success as a failure;
- raw HTTP request-target evidence must not be silently replaced by a normalized/decoded alias before route authority is selected;
- expected serving-evidence expiry and integrity/authorization failure must remain typed as different outcomes;
- inbound request-body memory/work must be bounded independently; elapsed-time-only truncation is not a substitute for protocol lifecycle authority;
- outbound response metadata/content must be completely validated before the first irreversible response-start when the owner chooses a complete non-streaming response;
- server/connection/cancellation failures are lifecycle evidence and must not be misclassified as local capability-shape defects or recursively serialized as another HTTP response;
- Draft implementation, source-local tests, or process-local receipts are not protected or released authority; and
- the final buyer path must include every actually deployed edge/composition/owner/PostgreSQL layer and meet the applicable p95 <=20 ms target without benchmark exclusions.

## Decision

The buyer-visible “Orgmetra Gateway” has two distinct internal responsibilities.

1. **Shared edge transport runtime, externally owned and optional unless a deployment requires it.** It owns connection/proxy/TLS mechanics, bounded transport resources, drain/shutdown, and low-cardinality transport telemetry within its released contract.
2. **Orgmetra product-composition application.** It owns product-facing authentication integration, runtime-principal projection, admitted route selection, owner API compatibility, exact composition generation/deployment state, activation/re-admission coordination, request-time serving currentness, the product-side ASGI request/response lifecycle, readiness, and end-to-end preservation of downstream semantics.

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

### Infer ordinary service unavailability from authorization/integrity exception text

Rejected. Expiry is an expected serving-liveness outcome while clock rewind, malformed durable evidence, retargeting, and authorization mutation are integrity/security failures. The durable owner must issue separate typed outcomes and the HTTP layer may project only the expected conflict family to ordinary unavailability.

### Treat callable invocation timing as proof of a bad ASGI capability

Rejected. ASGI supplies awaitable `receive`/`send` callables, but a callable may raise a server/runtime failure during invocation or while awaited. Composition proves only demonstrable shape defects (non-callable or a normal non-awaitable return) locally; invocation/await exceptions and cancellation retain server/caller lifecycle meaning.

### Send response-start before validating the complete response we already hold

Rejected. If a later body/framing error is found after `http.response.start`, the response is already partially committed and cannot safely be replaced by another problem response. The complete-response owner validates start metadata, terminal body and framing before the first send.

### Let application code choose outbound Transfer-Encoding

Rejected. The ASGI HTTP protocol server owns transfer coding. A complete-response owner rejects application-supplied `Transfer-Encoding` and separately validates any `Content-Length` it accepts against the selected representation/no-content semantics.

## Evidence layers

Evidence layers are intentionally non-interchangeable.

### Process-local structural evidence

`OwnerApiRelease`, `CompositionRoute`, `CompositionGeneration`, `AdmissionReceipt`, `DeploymentIdentity`, `ReleasedAuthorityEvidence`, `OwnerOperationObservation`, and `ActivationAdmissionEvidence` use process-local construction/issuance integrity where applicable. Valid-looking low-level mutation of an already-constructed object into another semantic meaning is rejected; new legitimate semantics require a new value.

The package-root `AuthorizedPostgresActivationRegistry` also binds the admitted evidence provider, validation clock, generation registry, structural activation registry, and their PostgreSQL connection factories to a construction snapshot. It checks that capability identity before durable reads and around the external callback. This protects checked-as-used local capability meaning, but remains process-local defense in depth.

Python object identity, a frozen dataclass, a caller digest, or a receipt-shaped value is not durable release/deployment authority.

### Durable generation/configuration authority — 0018

Migration `0018_product_composition_generation_registry.sql` persists normalized generation, owner-release, route, and route-method material. One `generation_id` cannot acquire two semantic meanings. Durable rows reconstruct fresh canonical values and reproduce the configuration digest; a stored digest alone is insufficient. Generation material is append-only and destructive rewrite/truncation is rejected.

0018 publishes the generation registry and its mutation guards atomically. It also pins object publication to trusted `public` rather than trusting caller `search_path`. #436 exact `30d89fa8f4ba95d7ddb84dde8e3b7e5faebf0343` is the current Draft implementation authority for this layer.

### Durable activation/recovery/currentness authority — 0019 through 0025

The ordered composition migration chain is **0018 -> 0019 -> 0020 -> 0021 -> 0022 -> 0023 -> 0024 -> 0025**.

- **0019** introduces non-PII `(deployment_id, environment_id)` identity, content-addressed external evidence, exact owner-operation observations, and append-only activation events. Its relation/function/trigger publication is one transaction and explicitly targets `public`.
- **0020** refuses predecessor NULL-evidence activation history and makes current activation events evidence-bound. The authority upgrade is transactionally fenced so a predecessor writer cannot cross the preflight/constraint-promotion boundary.
- **0021** rejects future-dated or already-stale owner-operation observations against PostgreSQL wall clock, refuses grandfathered impossible predecessor history, and fences predecessor writers across the history scan and guard installation.
- **0022** persists each successful restart re-admission as append-only recovery-attestation history bound to the exact current activation sequence, generation, and fresh `authorization_action='recover'` evidence. Its table and guards publish atomically.
- **0023** makes direct activation and recovery writers acquire the same `product_composition_deployment` row lock before existing lineage/evidence triggers run. Product and direct-SQL writer serialization therefore share one database authority.
- **0024** verifies the critical public trigger functions and rebinds all 16 activation/recovery INSERT, append-only, and TRUNCATE triggers to explicit `public.<function>()` identities. Trigger-function provenance is independent of migration-session `search_path`.
- **0025** locks the parent generation authority plus all five activation/recovery relations and requires every child relation owner to match the owner of `public.product_composition_generation`. It rejects both split ownership and a uniform foreign transfer without silently repairing ownership with `ALTER OWNER`.

The full-chain hostile-search-path contract executes 0018→0025 from a caller-controlled schema and requires all nine composition authority relations to remain in `public`, no authority relation/function to appear in the decoy schema, and all 16 activation/recovery triggers to bind trusted public functions.

`recover_active_route_snapshot()` is the startup/reload acquisition path. `current_route_ids_for_snapshot()` is the request-time PostgreSQL linearization boundary for current activation, exact/latest recovery attestation, database-owned recovery time, clock rewind, and evidence expiry. Expected expiry is a typed serving conflict; integrity/security failures remain authorization/integrity failures. No deployment lock is held across owner HTTP I/O.

### Transition and recovery evidence

Remote evidence acquisition stays outside the deployment-row lock. Activation/rollback obtains external evidence first, then the structural path locks the deployment, compares the exact prior sequence, reconstructs durable generation material, persists/verifies the evidence bundle, and appends the transition.

Recovery first reads the active durable event/generation and requires historical activation evidence, obtains fresh `recover` evidence outside the lock, then locks the deployment and requires the activation sequence and generation to remain exactly what was externally verified. It reconstructs the generation again, persists/verifies fresh evidence, and appends the next recovery attestation in the same local transaction.

Fresh recovery evidence is validated against the admitted local clock before the commit-capable call. PostgreSQL independently applies database-clock freshness while inserting evidence and the attestation. Once `recover_active_authorized()` returns, the durable transaction is committed; the product wrapper does not perform another fallible local-clock or capability decision that could report a false failure after that commit. A later request may fail closed if runtime capability integrity has been lost, but the committed attestation is not retrospectively reclassified.

## Product-composition request and HTTP contract

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
- ASGI `raw_path` remains the request-target evidence boundary when required by the product route profile; decoded path material cannot silently establish a different canonical route.
- malformed method syntax is distinct from a syntactically valid method outside the implemented composition profile, and both are distinct from a method not declared by the selected Path Item.
- `Allow` is derived from request-time currently serviceable selected-resource authority. A temporarily unavailable resource may legitimately emit an empty `Allow`.
- GET and HEAD share selected-resource authority where the GET representation is authoritative; HEAD suppresses response content without inventing a separate representation owner.

Product composition does not invent local retry, idempotency, concurrency, replay, or scientific-state taxonomies. Those remain released owner truth.

## ASGI request/response lifecycle

The product-side application contract follows ASGI 3 and the HTTP/WebSocket sub-specification rather than treating Python call timing as protocol semantics.

Inbound request bodies are read from `http.request` events under separate content-byte and receive-event budgets. Missing/invalid event shape fails closed; `http.disconnect` remains a peer lifecycle signal. A non-callable `receive` or a normal non-awaitable return is a local capability-shape defect. Invocation/await exceptions and cancellation propagate as server/caller lifecycle evidence.

Outbound core response events are limited to the currently owned `http.response.start` / `http.response.body` profile. Response status is 100..599, field names are lowercase RFC 9110 tokens, invalid field control octets are rejected, and trailers/extensions fail closed until a scope-aware owner explicitly negotiates and completes them. `send` follows the same capability-shape rule as `receive`: only non-callable/non-awaitable shape is reclassified locally; invocation/await failure, closed-connection `OSError`, and cancellation retain server lifecycle meaning.

For a complete non-streaming response, start metadata and terminal body are validated before the first transport send. The owner derives no-content behavior for HEAD/204/205/304, rejects application-supplied `Transfer-Encoding`, validates explicit `Content-Length` against the representation/no-content rules, and detaches validated header pairs from caller-owned mutable containers before the first await. Once response-start has been sent, an outbound transport failure is not recursively converted into another problem response.

## Authentication, identity projection, and authorization

Keyverse remains identity/issuer authority. Orgmetra identity/ACL owners retain durable subject-to-Person binding and consumer ACL. Domain owners retain purpose/resource authorization.

Composition may map a verified subject only to a namespaced opaque runtime actor reference through versioned Orgmetra ACL evidence. Caller-controlled organization/workspace/purpose fields do not override authenticated/projected evidence. Business purpose is propagated as downstream authorization input and never self-authorizes.

Production activation requires immutable released Keyverse/Orgmetra policy coordinates and exact owner-operation evidence. Synthetic release locators/digests are test fixtures only and cannot establish buyer-ready authority.

## Idempotency, retries, cancellation, errors, and scientific state

Composition forwards canonical owner-required idempotency and optimistic-concurrency coordinates unchanged. Automatic retry is deny-by-default unless the exact released owner operation contract proves replay safety for the observed request state. An ambiguous post-commit transport failure never becomes a fresh mutation.

User cancellation, upstream cancellation, owner timeout, composition administrative timeout, edge timeout, peer disconnect, response-send connection loss, and other connection failures remain distinguishable evidence.

Owner HTTP status and versioned error/problem identity are preserved unless a separately versioned product contract defines a safe translation. Authorization denial, stale conflict, unavailable owner, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence never becomes success. Client-visible failures exclude credentials, restricted HR payloads, stack traces, internal topology, and raw internal trace identifiers.

## Operability and readiness

Edge liveness, composition liveness, configuration validity, generation/activation validity, request-time currentness, identity-contract admission, per-owner route admission, fresh recovery re-admission, and buyer product readiness are separate signals. A process-local admission receipt is not buyer-readiness evidence.

Activation is generation-atomic. Rollback reactivates previously persisted immutable generation material only after current external authority and owner compatibility are re-admitted. Successful recovery survives process exit as a separate durable attestation rather than rewriting the historical activation event.

Success, rejection, cancellation, timeout, disconnect, partial response, and owner-unavailable paths release request tasks, buffers, upstream/client connections, and temporary state. Shared-edge and composition drain semantics are tested together when both layers are deployed.

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
- no expected serving expiry conflated with clock rewind/retarget/malformed durable authority;
- no concurrency regression that relies only on arbitrary scheduler sleep to prove hostile interleaving;
- no same-hierarchy path aliases, cross-owner ambiguous overlap, split GET/HEAD authority, URI dot-segment alias, or repeated template expression;
- no request-body path with unbounded retained bytes or unbounded receive-event amplification;
- no invalid/mutable caller response field allowed to change meaning after validation and before transport;
- no application-owned `Transfer-Encoding` in the complete-response profile;
- no response-start emitted before known terminal response/framing validation succeeds;
- browser CORS/CSRF/cookie/session behavior explicit when used; and
- every composition/configuration/deployment/recovery change attributable and auditable.

## Performance evidence

Applicable commercial paths measure the complete asynchronous deployment:

`client/k6 -> [shared edge if deployed] -> Orgmetra composition -> owner HTTP -> PostgreSQL -> owner -> composition -> [edge] -> client`

For paths designated applicable to the commercial target, p95 must be <=20 ms. Evidence reports edge, composition, and owner costs separately. An in-memory router, mocked owner, reduced sample, discarded slow request, disabled auth/audit, skipped database, or warm-cache-only subset cannot establish the SLO.

## Risks and effects

The durable-authority design adds schema, lock, migration, test, and operational surface. This is accepted because configuration, activation, recovery, request-time currentness, and external authorization need different lifecycles and must remain reconstructable after process exit.

Migration-level provenance checks do not themselves prove least-privilege production database-role deployment. Runtime/migrator role separation and privileges remain deployment evidence and must be demonstrated before release. A superuser or object owner can defeat ordinary DDL/DML guards; the production role model therefore cannot be inferred merely from successful migration tests.

Writer-conflicting migration fences can block or be blocked by active transactions. Upgrade rehearsal must measure lock acquisition, timeout/abort behavior, rollback, and retry on supported PostgreSQL deployment paths.

The bounded OpenAPI/ASGI profile may reject valid future owner or protocol-extension forms. Expansion is deliberate: a released owner need, compatibility contract, scope-aware negotiation where applicable, tests, and architecture review must precede a wider dialect.

## Verification and integration authority

#433 remains Proposed until independent architecture admission. This source currentization is intentionally code-current with the Draft implementation stack through #446 exact `7954f5bf606584ddb5bbcd29e1b64e49041b9409`; it does **not** convert those Drafts into protected/released truth and it does not claim their runtime GREEN.

Canonical execution is a real prerequisite, not a queue wait. Current `Foundation CI` is filtered to pull requests whose base is `develop`, while the composition implementation is an intentional stacked PR chain; current Foundation service execution is also filename-specific and does not discover `services/product-composition-api`. Consequently exact #446 has no PR-triggered Foundation run even though its service pyproject requires 100% branch/statement coverage. #260 owns repository-level service discovery/runtime compatibility and #261 owns installed-wheel acceptance; #311 owns fail-closed PostgreSQL contract discovery/execution. These owners must be repaired/integrated through their canonical Foundation path, not copied into #446 or replaced with a feature-local workflow.

#311 itself remains stacked on #259 and therefore demonstrates the same base-filter limitation: its exact candidate has no protected-base Foundation admission until the Foundation stack is normally reconciled. This is a Foundation owner-path dependency, not evidence that #446 is GREEN.

#340 remains an inherited Foundation prerequisite. No leaf shim, synthetic status, no-op rerun, routine administrator bypass, force-push/destructive rebase, self-approval, or gate weakening is authorized.

`API-01` remains Planned under #100 because no protected deployable buyer path exists.

## RED -> GREEN acceptance

GREEN requires all of the following on current protected/released truth:

- supported deployable HTTP product composition bound to immutable generation/configuration/deployment identity;
- released Keyverse consumer evidence and released Orgmetra ACL/purpose evidence;
- released owner API/OpenAPI/artifact evidence and exact operation-level conformance;
- fail-closed generation-ID reassignment, partial registry writes, route/release mismatch, invalid activation/rollback/recovery evidence, concurrent state changes, migration publication/provenance races, stale/future evidence, mutation/truncation attempts, runtime-capability retarget, restart reconstruction, and serving-currentness drift;
- raw request-target, method, selected-resource, current `Allow`, GET/HEAD, request-body, response-event, response-completion/framing and connection-lifecycle contracts on one exact implementation tree;
- exact-head pytest plus 100% owned statement/branch/docstring/edge evidence where tooling exposes it;
- isolated PostgreSQL acceptance through ordered migrations 0018→0025;
- Foundation/SAST/Security/CodeQL plus qualifying independent review;
- supported Podman/Colima and Kubernetes deployment/recovery evidence;
- fault/security/recovery rehearsal; and
- full applicable buyer-path k6/E2E with p95 <=20 ms and no omitted deployed layer.

## Implementation and release order

1. Keep #432 as buyer-visible composition-gap owner and #433 Proposed until normal architecture admission.
2. Keep this ADR/TRACEABILITY/doctoring code-current with Draft implementation while clearly retaining the Draft/unverified evidence boundary.
3. Resolve #340 and canonical Foundation prerequisites through their owner lanes. #259/#260/#261 own package/service runtime and installed-artifact acceptance; #311 owns PostgreSQL contract discovery/execution. Do not create a feature-local quality workflow to manufacture stacked-PR evidence.
4. Once canonical Foundation capability reaches protected truth, composition ordinary-forward adopts it and executes one unchanged candidate including #434/#436/#437/#438/#439/#440/#442/#443/#444/#446, with ordered migrations 0018→0025.
5. Reacquire #433 exact-head checks and qualifying independent architecture review on the source-current documentation; only then may ADR 0432 be considered for Accepted/Ready.
6. Obtain actual immutable Keyverse/Orgmetra/owner releases and prove positive activation plus restart recovery against those releases.
7. Implement the deployable authenticated ASGI composition host and exact owner HTTP dispatch without taking HR domain truth; complete success-response, cleanup, pool, snapshot reload/invalidation, and scope-aware extension/trailer lifecycle.
8. Acquire security/fault/recovery and complete buyer-path performance evidence.
9. #51 reconciles protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and reseals `manifest.json` after architecture admission.
10. #100 changes durable gap state only when buyer/scientific truth actually changes.
11. Protected integration then immutable Orgmetra release with version/CHANGELOG/tag/package/SBOM/provenance/reproducibility/rollback evidence.

## Consequences

Generic transport remains reusable without acquiring product semantics. “Thin Orgmetra composition” means a small deployable application contract, not merely a configuration document. The buyer-visible Gateway cannot be claimed shipped until product composition, identity/ACL, required owner APIs, optional edge transport, immutable generation/deployment provenance, recovery/currentness, ASGI application/owner dispatch, and full-path performance evidence converge on protected/released truth.

The bounded OpenAPI/ASGI profile reduces unsupported surface now but leaves an explicit compatibility path: if a released owner requires valid OpenAPI forms outside the current dialect, cross-owner composition under one Path Item, streaming/trailers/extensions, or another protocol behavior, support expands deliberately with conformance, negotiated capability, security, and path/lifecycle-authority evidence rather than permissive parser drift.

## Follow-up

- Keep `docs/traceability/gateway-composition-boundary.md` on the same exact executable stack and evidence distinctions.
- Keep `docs/doctoring/gateway-composition-boundary-references.md` current for ASGI 3, HTTP/WebSocket ASGI 2.5, RFC 9110/9112, RFC 9457, OpenAPI and PostgreSQL authority used by executable decisions.
- Repair #260/#261/#311 canonical Foundation execution so the product-composition service and ordered PostgreSQL roots can be exercised after normal owner integration; do not copy those mutable owners into the composition leaf.
- Re-run exact-head architecture checks after every material ADR/TRACEABILITY/doctoring change; do not transfer predecessor GREEN.
- Require independent architecture review before changing Status from Proposed.
- Prove production database-role least privilege separately from migration trigger/owner provenance.
- Change buyer-visible gap truth only through #100 after protected deployable evidence exists.

## References

The focused APA 7th standards/research record is `docs/doctoring/gateway-composition-boundary-references.md`. Repository-owner capability evidence belongs in `docs/traceability/gateway-composition-boundary.md` rather than being presented as an external normative standard.
