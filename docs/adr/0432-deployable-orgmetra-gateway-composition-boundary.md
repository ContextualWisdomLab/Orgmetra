# ADR 0432: Deployable Orgmetra Gateway composition boundary

## Status

Status: Proposed

Issue owner: #432

This ADR is design authority only. It does not make a gateway, a shared edge runtime, an owner API, or an Orgmetra release production-authoritative. Protected `develop` remains the shipped source of truth until normal review, exact-head checks, protected integration, and release evidence exist.

## Context

Protected `ARCHITECTURE.md` places an Orgmetra Gateway between the role workspaces and independently owned domain services. Protected `docs/API_CONTRACT.md` also assigns the gateway Keyverse OpenID Connect validation before generated request validation reaches a domain handler. The executable repository, however, does not yet provide one supported deployable composition boundary for those independently versioned services.

That gap is not permission to create another HR bounded context. Person, Employment, Assignment, Organization, Position, Job Architecture, Talent, Performance, Assessment coordination, Workforce Validation, documents, integration state, and audit provenance remain owned by their existing contexts. The gateway is an application/edge adapter. It may authenticate, route, correlate, enforce coarse API capability, apply transport controls, and expose composition health; it must not become a second source of HR truth, purpose policy, idempotency truth, or scientific evidence.

CWL also has a shared edge-runtime owner, `ContextualWisdomLab/pingora-gateway`. Fresh verification on 2026-09-21 found no published immutable release. Its root PR #1 is still Draft and records a current supplier-admission security RED (`derivative 2.2.0` / RUSTSEC-2024-0388) plus incomplete exact-head central CodeQL evidence. A mutable branch, PR SHA, source copy, or floating image therefore cannot be admitted into Orgmetra production.

## Decision drivers

The supported product boundary must:

- preserve Orgmetra HR domain ownership and separately deployable owner APIs;
- consume only compatible released owner contracts and immutable deployment artifacts;
- keep Keyverse as identity authority while preserving downstream owner authorization;
- preserve owner idempotency, concurrency, error, and scientific-state semantics rather than translating them into weaker edge-local concepts;
- prevent cross-service SQL and copied sibling source/schema;
- provide one supportable local and Kubernetes composition/recovery path;
- fail closed when a route, owner contract, gateway runtime, or deployment identity is not verifiable;
- expose exact provenance for the runtime, Orgmetra composition configuration, admitted owner APIs, and route set; and
- meet applicable buyer-path performance targets with gateway overhead measured separately from owner execution.

## Alternatives

### A. Repository-owned thin BFF/runtime

Orgmetra could implement its own edge runtime and keep all product-specific routing in this repository.

Advantages:

- no external gateway release prerequisite;
- product-specific behavior can evolve in one repository.

Rejected as the default because generic proxy/runtime concerns would duplicate the shared CWL edge owner. It would add another connection-pooling, TLS, retry, shutdown, observability, and supplier-security surface to Orgmetra. Option A may be reconsidered only through a new decision if a released shared owner cannot satisfy measured product requirements without violating domain or security boundaries.

### B. Released shared edge owner plus thin Orgmetra composition contract

A generic CWL edge owner supplies the released runtime. Orgmetra owns only the product composition contract: route-to-owner admission, Keyverse-facing product authentication expectations, coarse operation capability, owner-contract coordinates, purpose/context propagation rules, and deployment provenance.

Selected as the target architecture.

Selection does not admit the current `pingora-gateway` Draft. Production admission requires a release-qualified shared runtime with immutable artifact identity, SBOM/provenance, supported configuration contract, security GREEN, rollback/recovery evidence, and compatibility with the exact Orgmetra composition contract. Until then, `API-01` remains RED and no mutable shared-gateway source is consumed.

### C. No product gateway; expose domain APIs directly

Each workspace/client could call domain services independently.

Rejected for the current architecture because it contradicts the protected product boundary and would push common route discovery, Keyverse token handling, transport policy, deployment discovery, and compatibility logic into multiple clients. It also makes it easier for browser/client code to diverge on tenant/actor/purpose handling. This option requires an explicit future architecture revision rather than accidental absence of a gateway implementation.

## Decision

Orgmetra will target a **released shared edge runtime plus a thin, versioned Orgmetra-owned composition contract**.

The shared edge runtime owns generic transport/runtime behavior. Orgmetra owns the product composition and admission rules. Domain services retain their own API/domain/persistence truth.

No production route is admitted merely because an upstream endpoint is reachable. Admission requires all of the following to be bound together:

1. a released shared-gateway contract and immutable runtime artifact digest;
2. an exact Orgmetra product release/source and immutable composition-config digest;
3. an owner service identity and released owner API contract version;
4. the exact owner OpenAPI digest used for compatibility validation;
5. a route identifier, path/method mapping, and logical upstream service reference;
6. coarse required scope/capability and explicit tenant/actor/purpose binding rules;
7. owner idempotency/concurrency/error-preservation policy; and
8. route-level admission/readiness evidence.

A Git commit SHA may be retained as provenance, but it does not replace a released consumer contract or immutable deployable artifact.

## Orgmetra composition contract

The implementation owner must introduce a versioned product contract equivalent to `orgmetra_gateway_composition.v1`. The exact serialization and package path are implementation decisions, but the semantic fields are mandatory.

### Deployment identity

- Orgmetra product release/version and source commit;
- Orgmetra composition-contract schema version;
- immutable composition-config digest;
- shared gateway owner, release/version, contract identity, and artifact/image digest;
- environment/deployment identifier that contains no credential or person/tenant PII; and
- generation/activation identity sufficient to prove which route set was live during an observation window.

### Route admission

Each route entry carries:

- stable `route_id`;
- HTTP path template and allowed method set;
- owning bounded-context/service identity;
- released owner API contract version and OpenAPI digest;
- logical upstream service reference rather than a copied service implementation;
- required coarse Keyverse scope/capability;
- authoritative tenant/actor/purpose input locations;
- idempotency handling mode;
- optimistic-concurrency and owner error-preservation mode;
- retry class; and
- whether the route is required for product readiness or an explicitly optional capability.

Route admission is deny-by-default. A route whose released owner contract is absent, incompatible, unverifiable, or different from the recorded digest is not exposed.

The composition contract must not merge independently versioned domain schemas into one monolithic domain model. Aggregated discovery is an inventory of admitted owner operations, not a transfer of ownership.

## Authentication and authorization

Keyverse remains the identity provider. The gateway validates the product-facing OpenID Connect bearer token against the configured released Keyverse contract and rejects invalid issuer, audience, signature, expiry, subject, tenant, actor, or required coarse capability before routing.

The gateway does not make the business purpose self-authorizing and does not replace downstream authorization. The owner service receives the authenticated request context and re-evaluates its purpose/resource/domain invariants. Caller-controlled duplicate identity fields that contradict the authoritative token/path/query/header binding fail closed rather than being silently preferred.

The initial design does not invent a new internal token or token-exchange protocol. If a future implementation replaces propagation of the original authenticated credential/context with a signed internal request-context token, that mechanism requires its own versioned security contract and threat-model evidence before use.

## Idempotency, retries, cancellation, and concurrency

The gateway never mints a second mutation idempotency truth. A client-supplied canonical `Idempotency-Key` is validated for shape where applicable and forwarded unchanged to the owning service, which remains authoritative for semantic digest, replay, committed result identity, and conflict handling.

Automatic retries are deny-by-default:

- safe/idempotent HTTP methods may be retried only within an explicitly bounded route policy consistent with RFC 9110 semantics;
- mutation retries are permitted only when the released owner contract explicitly guarantees replay safety for the same `Idempotency-Key` and the gateway preserves that exact key and command bytes/semantics;
- an ambiguous transport failure after a potentially committed non-replay-safe mutation is not converted into a fresh mutation attempt; and
- user cancellation, upstream cancellation, owner timeout, gateway administrative timeout, and connection loss remain distinguishable operator evidence.

The gateway forwards optimistic-concurrency coordinates unchanged. It does not replace owner `If-Match`, version, or expected-state semantics with a gateway-local version counter.

## Error and scientific-state preservation

The gateway preserves the owning service's HTTP status and versioned error/problem identity unless a separately versioned product contract explicitly defines a safe translation.

It must not convert authorization denial, stale-version conflict, owner unavailable, timeout, `verification_pending`, `not_verifiable`, invalid evidence, or scientific non-convergence into `200`, empty data, or a generic success shell.

RFC 9457 is the current IETF Problem Details standard and is the preferred target when an owner API publishes Problem Details. The gateway does not unilaterally rewrite an owner contract that still publishes another versioned error shape. Canonical protected API documentation must be reconciled by its existing writer if Orgmetra later standardizes the owner error contract on RFC 9457.

Client-visible errors must not expose stack traces, internal topology, credentials, raw restricted-HR payloads, or internal trace identifiers. A client-safe support reference may map to restricted telemetry.

## Operability and readiness

Liveness and composition readiness are separate.

- Process liveness reports whether the gateway runtime is running.
- Configuration validity reports whether the exact signed/digested Orgmetra composition can be parsed and verified.
- Contract admission reports each route's shared-runtime and owner-contract compatibility.
- Product readiness fails when a required route is unadmitted or its required owner dependency is not ready according to the declared route policy. Optional routes are surfaced explicitly as unavailable rather than silently omitted.

Startup and config activation are transactional at the route-set generation level: a partially validated generation does not become current. Rollback selects a previously admitted immutable generation and records the activation change. A config version must never route a newer client contract to an older incompatible owner while still claiming the newer deployment identity.

Connection pools, tasks, request bodies, upstream sockets, and temporary buffers must be released on success, rejection, cancellation, timeout, partial response, and downstream-unavailable paths. Shutdown drains bounded in-flight work without accepting new traffic after the configured admission fence.

## Performance evidence

For applicable ordinary buyer paths, acceptance measures the full asynchronous path:

`client/k6 -> shared gateway runtime -> owner HTTP service -> PostgreSQL -> owner response -> gateway -> client`

The commercial target is p95 <= 20 ms where the underlying owner path is designated applicable to that target. Evidence reports at least gateway queue/auth/serialization/upstream-pool/forwarding overhead separately from owner authorization/query/transaction cost.

Do not claim the buyer SLO from an in-memory router, mocked owner, reduced sample, excluded slow requests, disabled auth/audit, or warm-cache-only subset. Connection-establishment/cold and steady-state windows are reported separately when materially different; the acceptance claim states which operational window it covers.

If the target is missed, profile the measured bottleneck before changing language/runtime. A Rust hot-path change is justified by measured material cost, not by preference alone.

## Security and privacy invariants

- no cross-service SQL or shared write repository;
- no mutable sibling source/config, floating image/tag, or copied owner schema;
- no caller-controlled header may override a contradictory authenticated identity or purpose binding;
- no bearer credential, raw restricted-HR payload, tenant/person identifier, or high-cardinality sensitive value becomes an unbounded metric label;
- CORS, CSRF, cookie/session behavior, and browser credential handling are explicit product contracts when a browser form uses them;
- route inventory, readiness, and operator telemetry expose contract identities and safe support references without disclosing secrets or restricted records; and
- all deployment/config changes are attributable and auditable.

## Implementation and release order

The target architecture does not authorize premature integration. The causal order is:

1. shared gateway owner resolves its current supplier/security and hosted-gate REDs;
2. shared owner normally integrates a release-qualified runtime and publishes an immutable supported contract/artifact with SBOM, provenance, reproducibility, and rollback evidence;
3. Orgmetra implements the thin composition contract/ACL against that release, without copied shared-runtime source;
4. owner domain APIs used by the composition publish compatible released OpenAPI contracts;
5. RED acceptance covers missing/incompatible routes, contradictory identity, owner-denied authorization, ambiguous mutation failure, idempotency/concurrency divergence, stale config, downstream failure, cleanup, and cross-schema prohibition;
6. exact-head GREEN includes Podman/Colima composition, supported Kubernetes deployment, realistic k6/E2E, recovery/rollback, security, and current protected workflow evidence;
7. canonical `ARCHITECTURE.md`, TRD, API, SECURITY, THREAT_MODEL, TEST_STRATEGY, OPERABILITY, TRACEABILITY, baseline, and deterministic manifest are reconciled only through their existing single-writer lanes; and
8. normal protected integration precedes version/tag/package/immutable Orgmetra release.

## Consequences

Positive:

- generic edge runtime concerns stay with one reusable owner;
- product route/purpose/admission truth stays in Orgmetra;
- domain services remain independently versioned and authoritative;
- production composition becomes inspectable and reproducible rather than implied by an architecture diagram; and
- an unavailable or incompatible owner contract fails closed instead of silently degrading into mutable-source coupling.

Costs and risks:

- Orgmetra cannot claim a deployable gateway product boundary until the shared runtime is release-qualified;
- two layers participate in authorization, so tests must prove gateway coarse capability never weakens owner resource/purpose rules;
- independently versioned owner APIs increase composition-admission and rollback complexity; and
- p95 <= 20 ms may require measured optimization in both edge and owner paths rather than one local code change.

## References

The focused APA 7th reference and verification record is maintained in `docs/doctoring/gateway-composition-boundary-references.md`.
