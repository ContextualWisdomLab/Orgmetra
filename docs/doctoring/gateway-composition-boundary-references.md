# Gateway composition boundary references

Verification date: 2026-09-21

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

RFC 3986 Sections 5.2.4 and 6.2.2.3 define complete `.` and `..` path segments as dot-segments removed during reference resolution/path normalization. Orgmetra therefore rejects those complete segments before route hashing/admission rather than letting one manifest identity normalize into another selected path. Ordinary dots inside other segments are not reinterpreted by this rule.

**Nottingham, M., Wilde, E., & Dalal, S. (2023). _Problem details for HTTP APIs_ (RFC 9457). RFC Editor. https://www.rfc-editor.org/rfc/rfc9457.html**

Where an owner publishes RFC 9457 Problem Details, product composition preserves owner status/problem identity and does not leak stack traces, credentials, restricted HR payloads, or topology. Protected Orgmetra APIs are not thereby presumed to have migrated to RFC 9457; canonical API standardization remains with the existing API/documentation owner lane.

### API contract description

**OpenAPI Initiative. (2026). _OpenAPI Specification v3.2.1_. https://spec.openapis.org/oas/v3.2.1.html**

OpenAPI Specification 3.2.1 is the current 3.2 patch release on this verification date. Protected Orgmetra documentation still records OpenAPI 3.2.0 as its HTTP contract language. Citing 3.2.1 here does not silently upgrade protected owner contracts; the path rules below are compatible with the existing 3.2 line and are used as fail-closed composition conformance constraints.

Two OpenAPI rules must remain distinct:

1. **Paths Object identity — Section 4.8.1.** Templated paths with the same hierarchy but different templated names MUST NOT exist because they are identical. Consequently `/v1/people/{person_record_id}` and `/v1/people/{worker_record_id}` are one OpenAPI path identity regardless of the operations attached to them. Orgmetra enforces one exact template string per hierarchy before configuration hashing. Distinct methods may coexist only under that same exact path template, subject to operation-authority rules.
2. **Path templating validity — Section 4.8.2.** Template expressions must be valid path-template coordinates and each path-parameter name maps to one template occurrence. Orgmetra rejects repeated expressions such as `/v1/tenants/{record_id}/people/{record_id}` before configuration hashing/admission rather than depending on framework-specific parameter-map behavior.

These normative OpenAPI path rules are separate from Orgmetra's HTTP operation-ownership policy. The GET/HEAD equivalence used for collision ownership is derived from RFC 9110, not OpenAPI. URI dot-segment rejection derives from RFC 3986. Orgmetra's added decision in all cases is to fail before invalid or ambiguous route material receives configuration identity.

OpenAPI does not establish semantic compatibility of two Orgmetra service releases, retry safety, buyer readiness, deployment fitness, durable generation identity, or route ownership. Those require executable owner/consumer evidence.

## Repository-owner capability evidence

These facts are not normative standards. They constrain architecture because CWL consumers must respect the released owner's actual supported contract rather than infer capability from repository existence.

### Orgmetra protected truth

On 2026-09-21 protected authority is `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`. Protected `ARCHITECTURE.md` documents a buyer-facing Gateway and protected `docs/API_CONTRACT.md` documents pre-handler Keyverse OIDC validation. Protected People and Job Analysis HTTP edges expose authenticator/principal ports rather than a released Keyverse verifier/ACL implementation. The protected executable repository still has no supported deployable multi-owner product-composition application. Those responsibilities are design obligations, not proof of shipped capability.

### Draft executable canary #434

Draft #434 exact authority is `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`, 74 commits / 13 changed files, all confined to `services/product-composition-api/**`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`.

Current executable evidence includes:

- deterministic config digest from canonical semantic route material;
- canonical Orgmetra release-locator attribution;
- pre-hash per-route and generation-wide validation;
- one exact owner release per `service_id`;
- owner-bound logical upstream identity;
- URI dot-segment rejection;
- repeated single-path template-expression rejection;
- one exact OpenAPI template identity per parameter-name-independent hierarchy, independent of HTTP method;
- distinct methods allowed on the same exact template string;
- separate effective-method collision checks with GET/HEAD as one selected-resource authority;
- no local retry/idempotency/concurrency taxonomy;
- canonical process-local `AdmissionReceipt` field binding and source-generation leasing;
- deterministic receipt route ordering;
- use-time nested graph/config revalidation; and
- process-local generation construction identity/live lineage protection.

The latest OpenAPI path-identity sequence is:

- `2b4f2211a2e332058bec31af11474d3937899855` — RED for same hierarchy/different template names under disjoint methods, plus positive control for different methods on the same exact template;
- `2c7bfcf75ec2d353d52ed86cbcd74dba5ddae3ea` — one exact template identity per parameter-name-independent hierarchy before hashing; and
- `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1` — executable documentation currentization.

Earlier retained ordinary-forward sequences include:

- `f7175e36... -> 105fa9a5... -> d3e24da9...` for generation-construction identity;
- `5bbd0187... -> 79279c21... -> db251db2...` for deterministic receipt ordering;
- `34a598ad... -> 8a1e8854... -> bdedbda0...` for GET/HEAD selected-resource ownership;
- `4c8d195d... -> e8931bc9... -> 8bdb2bb2...` for URI dot-segment identity;
- `b9777f69... -> ab35e5c3... -> 356fe9e9... -> 51a1ad47...` for one-release-per-owner-service coherence; and
- `acc7a471... -> bd43f474... -> 9ad27d83...` for repeated OpenAPI template-expression rejection.

The generation-construction and live-lineage rules are Orgmetra evidence-integrity requirements, not OpenAPI/OAuth/HTTP rules. GET/HEAD combines RFC 9110 selected-resource semantics with an Orgmetra ownership decision. Dot-segment rejection combines RFC 3986 normalization semantics with a fail-closed product decision. Same-hierarchy/different-template-name prohibition and path-template conformance come from OpenAPI; Orgmetra additionally requires those failures to occur before configuration identity is minted.

Earlier focused local coverage figures at predecessor `cb32ba828...` are predecessor mechanism evidence only. Material source/test writes followed. No predecessor workflow result substitutes for current exact-head coverage, Security, SAST, CodeQL, independent review, deployment, or release evidence.

Synthetic owner-release fixtures and process-local registries do not prove actual owner releases, Keyverse conformance, Orgmetra identity ACL, durable activation, deployment/recovery, commercial latency, protected integration, or immutable Orgmetra release.

### pingora-gateway owner contract

Fresh owner evidence records protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` with no immutable release. Its generic v1 contract remains single-upstream/transport-oriented and excludes product routing/auth/business semantics. The pg-erd migration composition does not become a generic Orgmetra route-policy contract. Orgmetra may consume a future released domain-neutral edge capability but must not copy mutable source/config or transfer product mapping/ACL authority to that owner.

### Keyverse and Orgmetra consumer ownership

On the same verification date, Keyverse protected authority was `main@7d9151cd2da260e118020c938c7358e2ee75d541` with no immutable consumer release. Keyverse #155 owns durable-subject trust semantics; #158 is the broader immutable domain-neutral OIDC RP release path. Orgmetra #295/#297 own durable subject-binding/consumer ACL and #65 owns purpose-bound authorization runtime integrity.

Product composition may perform only request-scoped projection over those contracts. It cannot widen the Keyverse claim model, infer Person identity from `sub`, cast `org`/`workspace` directly into HRIS tenant identity, or make role/scope/purpose self-authorizing.

## Why the selected split follows the evidence

The Proposed direction remains **released shared edge transport when available + separately deployable Orgmetra product composition**. This is an ownership decision, not a claim that two network hops are intrinsically better. Generic transport already has a reusable owner; that owner's current contract intentionally excludes Orgmetra product semantics; protected Orgmetra architecture still requires a coherent product boundary; and HR/identity/authorization/idempotency/concurrency/retry truth already has narrower owners.

If measurement shows material overhead, optimization follows profiling of the complete deployed path rather than collapsing ownership or silently moving product semantics into the reverse proxy.

## Evidence discipline

A standards citation, repository file, open PR, architecture diagram, synthetic fixture, frozen dataclass, process-local registry, or local unit suite is not GREEN commercial evidence. Acceptance still requires exact protected/released identities, current-head conformance/security tests, independent review, cryptographic identity verification, explicit ACL projection tests, immutable generation/activation/deployment evidence, fault injection, recovery/rollback evidence, and realistic k6/E2E measurements across every deployed layer and the owner PostgreSQL path.
