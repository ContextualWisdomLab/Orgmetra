# Gateway composition boundary references

Verification date: 2026-09-21

Scope: primary standards and authoritative specifications used by ADR 0432, plus live repository-owner capability evidence needed to avoid assigning product semantics to the wrong runtime. Standards constrain protocol behavior; they do **not** prove that Orgmetra, Keyverse, pingora-gateway, or any owner API is released, deployed, conformant, secure, or within the commercial latency target.

## Source-to-decision traceability

### OAuth and OpenID Connect

**OpenID Foundation. (2023). _OpenID Connect Core 1.0 incorporating errata set 2_. https://openid.net/specs/openid-connect-core-1_0.html**

The OpenID Foundation approved the second errata set in December 2023. OpenID Connect remains the published authentication/claims contract referenced by protected Orgmetra architecture. In 2025 the errata-set-2 Core specification was also published as ITU-T X.1285; that recognition does not change Keyverse/Orgmetra ownership.

Use in ADR 0432:

- Keyverse remains identity/issuer authority;
- the Orgmetra product-composition application consumes a released relying-party verifier/profile rather than becoming a credential issuer;
- verified issuer/subject/audience and claim coordinates still require explicit Orgmetra consumer/ACL handling before they become runtime tenant/actor/operation-capability coordinates; and
- downstream owner authorization remains separate from authentication and coarse operation admission.

Not established by this source:

- that Orgmetra's current Keyverse integration is conformant;
- that Keyverse `org`, `workspace`, `role`, or `sub` can be cast directly into an Orgmetra HRIS identifier;
- that every valid OIDC subject is eligible for durable RP/Person correlation;
- that forwarding a particular token or internally projected context between product composition and owner services is safe; or
- that a Keyverse or shared-edge release exists.

Durable-correlation eligibility therefore remains Keyverse owner truth. Keyverse #155 owns subject-assertion trust semantics for durable RP binding; the broader #158 immutable RP release envelope must adopt/reuse those semantics or prove complete verified succession. Orgmetra #295/#297 own durable subject-binding/consumer ACL behavior, and #65 plus domain owners retain purpose/resource authorization. ADR 0432 composes these authorities; it does not replace them.

**Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). _Best current practice for OAuth 2.0 security_ (BCP 240, RFC 9700). RFC Editor. https://www.rfc-editor.org/rfc/rfc9700.html**

RFC 9700 is the IETF Best Current Practice for OAuth 2.0 security as of this verification date. It updates security guidance associated with RFCs 6749, 6750, and 6819 and rejects several insecure historical patterns.

Use in ADR 0432:

- bearer-token handling at the product boundary is a security boundary, not generic header forwarding;
- redirect/browser behavior, if introduced, follows an explicit secure flow rather than a reverse-proxy default;
- authentication material and key-rotation failures fail closed rather than downgrade to weaker legacy handling; and
- an identity-backend outage does not authorize anonymous or decoded-only fallback.

Not established by this source:

- Orgmetra-specific tenant, actor, business-purpose, employment-policy, resource authorization, durable Person binding, or Keyverse-to-Orgmetra ACL semantics.

### HTTP semantics, retries, and errors

**Fielding, R., Nottingham, M., & Reschke, J. (2022). _HTTP semantics_ (RFC 9110). RFC Editor. https://www.rfc-editor.org/rfc/rfc9110.html**

RFC 9110 Section 9.2.2 defines HTTP method idempotency and why some idempotent requests can be retried after communication failure.

Use in ADR 0432:

- transport retry policy distinguishes protocol-level idempotent methods from application commands;
- POST/mutation replay is not made safe by either shared edge transport or product composition; replay requires the released owner service's exact `Idempotency-Key` contract; and
- an ambiguous failure after a potentially committed non-replay-safe mutation does not justify a fresh mutation attempt.

Not established by this source:

- Orgmetra semantic command digests, first-commit replay, optimistic-concurrency or employment-fact idempotency semantics. Those remain owner-domain evidence.

**Nottingham, M., Wilde, E., & Dalal, S. (2023). _Problem details for HTTP APIs_ (RFC 9457). RFC Editor. https://www.rfc-editor.org/rfc/rfc9457.html**

RFC 9457 is the current IETF Standards Track Problem Details specification and obsoletes RFC 7807. Its security considerations warn against leaking sensitive implementation details.

Use in ADR 0432:

- where an owner publishes RFC 9457 Problem Details, product composition preserves owner status and problem identity rather than coercing failure into success;
- client-visible errors do not expose stack dumps, credentials, internal topology or restricted HR data; and
- error normalization is an explicit versioned product/owner decision, not an implicit behavior of shared proxy transport.

Not established by this source:

- that protected Orgmetra APIs already publish RFC 9457. Protected `docs/API_CONTRACT.md` currently defines a versioned Orgmetra error shape; canonical standardization, if chosen, belongs to the existing API/documentation owner path.

### API contract description

**OpenAPI Initiative. (2025). _OpenAPI Specification v3.2.0_. https://spec.openapis.org/oas/v3.2.0.html**

Protected Orgmetra documentation already uses OpenAPI 3.2.0 as its HTTP contract language.

Use in ADR 0432:

- route admission is tied to a released owner API version and exact OpenAPI digest;
- the product-composition inventory remains an admitted-operation catalogue, not a monolithic copied domain schema; and
- a missing or incompatible owner contract leaves a route unavailable.

Not established by this source:

- semantic compatibility of two Orgmetra service releases. That requires executable consumer/provider conformance evidence.

## Repository-owner capability evidence

These facts are not normative standards. They constrain architecture because CWL requires consumers to respect the released owner's actual supported contract rather than infer capability from repository existence.

### Orgmetra protected truth

On 2026-09-21:

- protected authority was `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`;
- protected `ARCHITECTURE.md` documented a buyer-facing Orgmetra Gateway and assigned API aggregation, tenant context, purpose-bound authorization, idempotency and event-envelope handling to the runtime layer;
- protected `docs/API_CONTRACT.md` documented pre-handler Keyverse OIDC validation at that boundary;
- protected People and Job Analysis HTTP code exposed injected `TokenAuthenticator` / `AuthenticatedPrincipal` ports rather than a released Keyverse verifier/ACL implementation; and
- the executable repository still had no supported deployable application that composes independently versioned owner APIs into that buyer-facing boundary.

Those protected responsibilities are therefore design obligations, not proof that one executable gateway currently exists.

### pingora-gateway owner contract

Fresh verification of `ContextualWisdomLab/pingora-gateway` found:

- protected authority `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991`;
- no published immutable GitHub Release;
- root PR #1 exact `38db1949354f5721dc0ecfeea395bcf958a64ace`, still Draft, with a PR-introduced `derivative 2.2.0` / `RUSTSEC-2024-0388` supplier-admission RED and no authenticated current-foundation central CodeQL verdict;
- its generic v1 `API_CONFIG_CONTRACT.md` requires **exactly one upstream** and explicitly excludes route tables, user-selected destinations, credentials, retry counts and other product semantics; and
- authentication/authorization, tenant/business routing, Keyverse identity and application semantics remain outside the reusable edge owner.

A separate pg-erd migration stack characterizes `backend` / `frontend` multi-route composition. That stack's own authority explicitly says its bounded Admin Config does **not** become a generic multi-route product policy language. It is evidence that the shared runtime can host a specific migration composition, not an owner contract authorizing Orgmetra to reuse that mutable path as general product routing.

Consequences for ADR 0432:

- a future immutable release of the current generic v1 edge contract would still be transport capability, not Orgmetra multi-owner product composition;
- Orgmetra must not copy mutable pingora source/config or repurpose the pg-erd route model to make the architecture diagram look implemented;
- reusable edge transport may sit in front of the product, but Orgmetra still needs a deployable product-composition application that owns product route admission and identity-context projection without owning HR domain truth; and
- if pingora-gateway later publishes a domain-neutral multi-route capability, Orgmetra may consume that released capability, but its product mapping/ACL and owner-conformance evidence remain Orgmetra authority.

### Keyverse and Orgmetra consumer ownership

On the same verification date:

- `ContextualWisdomLab/keyverse` protected authority was `main@7d9151cd2da260e118020c938c7358e2ee75d541` with no published immutable consumer release;
- protected Keyverse kept the RP mapper profile closed to one self-pinned audience plus optional canonical `role`, `org`, and `workspace` claims rather than Orgmetra-specific HR claims;
- Keyverse #155 owned narrower durable-subject assertion/correlation trust semantics;
- Keyverse #158 was the broader immutable domain-neutral OIDC RP release path and had been currentized to adopt/reuse #155 instead of creating a parallel subject-trust contract;
- Orgmetra #295/#297 owned durable subject-binding/consumer ACL; and
- Orgmetra #65 owned purpose-bound authorization runtime integrity.

The product-composition application may therefore perform only the runtime projection needed to route one verified request. It cannot widen the Keyverse claim model, infer Person identity from `sub`, cast `org`/`workspace` directly into HRIS tenant identity, or make `role`/scope/purpose self-authorizing.

## Why the selected split follows the evidence

The selected Proposed direction is **released shared edge transport when available + a separately deployable Orgmetra product-composition application**.

This is not a claim that two network hops are inherently superior. It is an ownership decision derived from the current contracts:

- generic transport/runtime mechanics already have a reusable owner;
- the reusable owner's current generic contract intentionally does not own Orgmetra product route/auth/business semantics;
- protected Orgmetra architecture nonetheless requires a coherent product composition boundary; and
- HR/identity/authorization truth already has narrower owners that the composition layer must preserve.

A future implementation may deploy the composition application behind a release-qualified shared edge or behind another approved ingress. The product contract remains the same. If measurement shows an unacceptable extra hop, optimization occurs against the measured deployed path rather than by collapsing ownership and silently moving product semantics into a reverse proxy.

## Evidence discipline

A standards citation, repository file, open PR, or architecture diagram is not GREEN implementation evidence. Commercial acceptance still requires exact protected/released identities, current-head conformance/security tests, cryptographic identity verification, explicit ACL projection tests, fault injection, deployment/recovery evidence and realistic k6/E2E measurements across every actually deployed layer and the owner PostgreSQL path. Synthetic fixtures may prove mechanism behavior but cannot alone establish buyer-path availability, latency, privacy, identity conformance, or scientific correctness.
