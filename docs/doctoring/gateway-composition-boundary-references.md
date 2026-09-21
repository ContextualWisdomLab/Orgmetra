# Gateway composition boundary references

Verification date: 2026-09-22

Scope: primary standards and authoritative specifications used by ADR 0432, plus live repository-owner capability evidence needed to avoid assigning product semantics to the wrong runtime. Standards constrain protocol behavior; they do **not** prove that Orgmetra, Keyverse, pingora-gateway, or any owner API is released, deployed, conformant, secure, or within the commercial latency target.

## Source-to-decision traceability

### OAuth and OpenID Connect

**OpenID Foundation. (2023). _OpenID Connect Core 1.0 incorporating errata set 2_. https://openid.net/specs/openid-connect-core-1_0.html**

OpenID Connect remains the authentication/claims contract referenced by protected Orgmetra architecture. Keyverse remains identity/issuer authority. Orgmetra consumes a released relying-party verifier/profile and applies its own versioned ACL before any verified subject or organization/workspace claim becomes a runtime actor or tenant coordinate. Downstream purpose/resource authorization remains separate.

This source does not establish Orgmetra-specific tenant semantics, durable Person binding, authorization, or the existence of a Keyverse release. Those remain Keyverse #155/#158 and Orgmetra #295/#297/#65/domain-owner evidence.

**Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). _Best current practice for OAuth 2.0 security_ (BCP 240, RFC 9700). RFC Editor. https://www.rfc-editor.org/rfc/rfc9700.html**

RFC 9700 is the current OAuth 2.0 security BCP. It supports treating bearer-token verification, key rotation, redirect/browser behavior, and identity-backend failure as explicit security boundaries. It does not define Orgmetra tenant, actor, business-purpose, Person-binding, or HR authorization semantics.

### HTTP semantics, retries, and errors

**Fielding, R., Nottingham, M., & Reschke, J. (2022). _HTTP semantics_ (RFC 9110). RFC Editor. https://www.rfc-editor.org/rfc/rfc9110.html**

RFC 9110 Section 9.2.2 constrains method idempotency and retry semantics. Section 9.3.2 defines HEAD as GET semantics without response content. ADR 0432 therefore uses HTTP semantics only as a protocol constraint: product composition has no second retry taxonomy, positive replay requires the exact released owner contract, ambiguous mutation failure never authorizes a fresh mutation, and GET/HEAD are one selected-resource collision authority. The actual declared route method set remains exact contract material.

RFC 9110 does not determine which Orgmetra bounded context owns a route or make an application mutation replay-safe.

**Berners-Lee, T., Fielding, R., & Masinter, L. (2005). _Uniform Resource Identifier (URI): Generic Syntax_ (RFC 3986). RFC Editor. https://www.rfc-editor.org/rfc/rfc3986.html**

RFC 3986 Sections 5.2.4 and 6.2.2.3 define complete `.` and `..` path segments as dot-segments removed during reference resolution/path normalization. Orgmetra rejects those complete segments before route hashing/admission rather than letting one manifest identity normalize into another selected path. Ordinary dots inside other segments are not reinterpreted by this rule.

**Nottingham, M., Wilde, E., & Dalal, S. (2023). _Problem details for HTTP APIs_ (RFC 9457). RFC Editor. https://www.rfc-editor.org/rfc/rfc9457.html**

Where an owner publishes RFC 9457 Problem Details, product composition preserves owner status/problem identity and does not leak stack traces, credentials, restricted HR payloads, or topology. Protected Orgmetra APIs are not thereby presumed to have migrated to RFC 9457; canonical API standardization remains with the existing API/documentation owner lane.

### API contract description

**OpenAPI Initiative. (2025). _OpenAPI Specification v3.2.0_. https://spec.openapis.org/oas/v3.2.0.html**

Protected Orgmetra `docs/API_CONTRACT.md`, `docs/TRD.md`, `schemas/openapi.yaml`, Foundation validation, and contract tests explicitly declare OpenAPI 3.2.0. That remains the product contract until the canonical API owner changes it.

**OpenAPI Initiative. (2026). _OpenAPI Specification v3.2.1_. https://spec.openapis.org/oas/v3.2.1.html**

OpenAPI Specification 3.2.1 is the current 3.2 patch release on this verification date. OAS Section 2.1 states that the `major.minor` portion designates the feature set and patch releases address errors or clarifications; tooling should not distinguish patch releases as different feature sets. Citing 3.2.1 therefore supplies the current patch-level interpretation of the 3.2 line; it does **not** silently upgrade Orgmetra's protected 3.2.0 contract.

Four OpenAPI facts matter separately:

1. **Paths Object identity — Section 4.8.1.** Templated paths with the same hierarchy but different templated names MUST NOT exist because they are identical. `/v1/people/{person_record_id}` and `/v1/people/{worker_record_id}` are one path identity regardless of attached HTTP operations. Orgmetra enforces one exact template string per hierarchy before configuration hashing.
2. **Concrete-before-template matching — Section 4.8.1, with the Section 4.8.2.1 example.** Concrete non-templated paths are matched before templated counterparts; the specification illustrates `/pets/mine` taking precedence over `/pets/{petId}`. A composition layer must not reject this valid owner API shape merely because both paths can match the same concrete request.
3. **Path-template grammar and validity — Section 4.8.2.** OAS permits path segments composed from RFC 3986 `pchar` literals and template expressions and requires each template expression to appear at most once in a path template.
4. **Path Item operations — Section 4.9.1.** The 3.2 feature set includes the usual fixed HTTP operations plus `TRACE`, `QUERY`, and `additionalOperations` for additional methods.

The #434 canary deliberately implements a **narrower Orgmetra product-route profile** than the complete OAS 3.2 grammar. It accepts restricted ASCII literal segments, whole-segment lower-snake-case template expressions, and exactly `DELETE`, `GET`, `HEAD`, `OPTIONS`, `PATCH`, `POST`, and `PUT`. OAS-valid forms outside that bounded profile—including mixed literal/template segments, unsupported `pchar` literals, `TRACE`, `QUERY`, and `additionalOperations` methods—fail closed before configuration identity. This is an Orgmetra product constraint, not an OpenAPI requirement. Broader support requires a released owner use case and explicit conformance tests; framework acceptance alone is not evidence.

Orgmetra also adds a narrower product rule to concrete-before-template matching: deterministic overlap is admitted only when the concrete and templated routes bind the same exact owner release and declare the same exact method set. Cross-owner overlap remains fail-closed, and ambiguous overlap between two templated paths remains fail-closed. The same-method-set condition prevents composition from inventing a fallback to a templated operation when OpenAPI first selects a concrete Path Item that does not declare that method. Broadening this behavior requires released-owner conformance evidence, not framework-specific routing assumptions.

These OpenAPI rules remain separate from HTTP operation ownership. GET/HEAD collision equivalence is derived from RFC 9110, not OpenAPI. URI dot-segment rejection derives from RFC 3986. Orgmetra's additional evidence rule is that invalid or ambiguous route material must fail before configuration identity is minted.

OpenAPI does not establish semantic compatibility of two Orgmetra releases, retry safety, buyer readiness, durable generation identity, or HR bounded-context ownership. Those require executable owner/consumer evidence.

## Repository-owner capability evidence

These facts are not normative standards. They constrain architecture because CWL consumers must respect the released owner's actual supported contract rather than infer capability from repository existence.

### Orgmetra protected truth

On 2026-09-22 protected authority remains `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`. Protected `ARCHITECTURE.md` documents a buyer-facing Gateway and protected `docs/API_CONTRACT.md` documents pre-handler Keyverse OIDC validation. Protected People and Job Analysis HTTP edges expose authenticator/principal ports rather than a released Keyverse verifier/ACL implementation. The protected executable repository still has no supported deployable multi-owner product-composition application. Those responsibilities are design obligations, not proof of shipped capability.

### Draft executable canary #434

Draft #434 exact authority is `a1b903cabc900b33ac4da36f3781bddc50cf57ee`, with 85 ordinary-forward commits / 14 changed files confined to `services/product-composition-api/**`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`.

Current executable evidence includes deterministic config hashing, canonical Orgmetra release attribution, pre-hash route-set validation, one release per owner service, owner-bound upstream identity, URI dot-segment and repeated-expression rejection, one exact template identity per OpenAPI path hierarchy, deterministic same-owner concrete-before-template precedence, cross-owner/ambiguous-template rejection, separate GET/HEAD effective-authority checks, process-local receipt/source-generation integrity, deterministic receipt ordering, use-time graph revalidation, and process-local generation lineage protection.

The latest standards-profile sequence is:

- `7a30ccd000c5e7b5a69e6f872277e7cf8fab2437` — adds executable controls for OAS-valid shapes outside the bounded profile and a documentation-contract RED because the predecessor README did not state that #434 is only a strict product profile;
- `a1b903cabc900b33ac4da36f3781bddc50cf57ee` — states the protected OpenAPI 3.2.0 contract, current 3.2.1 patch-level interpretation boundary, exact admitted route/method dialect, fail-closed unsupported forms, and evidence threshold for expansion.

The deterministic-precedence sequence remains `fd7e7c69105fa2850dc30dd43014592f1a753eaa` -> `393cb561a1226529553baa6129378281cfba6f27` -> `a98dd5f7ffd175e2a7b3b5ca61255420f2959f8b`. The earlier path-key identity sequence remains `2b4f2211a2e332058bec31af11474d3937899855` -> `2c7bfcf75ec2d353d52ed86cbcd74dba5ddae3ea` -> `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`. Later test-only repairs aligned stale overlap assertions with the three-layer path model without weakening production admission.

The generation-construction/live-lineage rules are Orgmetra evidence-integrity requirements, not OpenAPI/OAuth/HTTP rules. GET/HEAD combines RFC 9110 semantics with an Orgmetra ownership decision. Dot-segment rejection combines RFC 3986 normalization with a fail-closed decision. Same-hierarchy identity, concrete-before-template precedence, and repeated-expression validity come from OpenAPI; the bounded route grammar/method whitelist and stricter overlap ownership rules are Orgmetra constraints.

Earlier focused local coverage figures at predecessor `cb32ba828...` are predecessor mechanism evidence only. Material source/test writes followed. Exact `a1b903ca...` currently has no PR-triggered hosted workflow evidence, so no current-head 100% coverage, Security, SAST, CodeQL, deployment, or release claim is made.

Synthetic owner-release fixtures and process-local registries do not prove actual owner releases, Keyverse conformance, Orgmetra identity ACL, durable activation, deployment/recovery, commercial latency, protected integration, or immutable Orgmetra release.

### pingora-gateway owner contract

Fresh owner evidence previously recorded protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` with no immutable release. Its generic v1 contract remains single-upstream/transport-oriented and excludes product routing/auth/business semantics. The pg-erd migration composition does not become a generic Orgmetra route-policy contract. Orgmetra may consume a future released domain-neutral edge capability but must not copy mutable source/config or transfer product mapping/ACL authority to that owner.

### Keyverse and Orgmetra consumer ownership

On 2026-09-22 Keyverse protected authority remains `main@7d9151cd2da260e118020c938c7358e2ee75d541` and the GitHub Release inventory is empty. Keyverse #155 owns durable-subject trust semantics; #158 is the broader immutable domain-neutral OIDC RP release path. Orgmetra #295/#297 own durable subject-binding/consumer ACL and #65 owns purpose-bound authorization runtime integrity.

Product composition may perform only request-scoped projection over those contracts. It cannot widen the Keyverse claim model, infer Person identity from `sub`, cast `org`/`workspace` directly into HRIS tenant identity, or make role/scope/purpose self-authorizing.

## Why the selected split follows the evidence

The Proposed direction remains **released shared edge transport when available + separately deployable Orgmetra product composition**. This is an ownership decision, not a claim that two network hops are intrinsically better. Generic transport already has a reusable owner; that owner's current contract intentionally excludes Orgmetra product semantics; protected Orgmetra architecture still requires a coherent product boundary; and HR/identity/authorization/idempotency/concurrency/retry truth already has narrower owners.

If measurement shows material overhead, optimization follows profiling of the complete deployed path rather than collapsing ownership or silently moving product semantics into the reverse proxy.

## Evidence discipline

A standards citation, repository file, open PR, architecture diagram, synthetic fixture, frozen dataclass, process-local registry, or local unit suite is not GREEN commercial evidence. Acceptance still requires exact protected/released identities, current-head conformance/security tests, independent review, cryptographic identity verification, explicit ACL projection tests, immutable generation/activation/deployment evidence, fault injection, recovery/rollback evidence, and realistic k6/E2E measurements across every deployed layer and the owner PostgreSQL path.
