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

RFC 9110 Section 9.2.2 defines HTTP method idempotency and the protocol conditions under which some requests may be retried after communication failure. Section 9.3.2 defines HEAD as identical to GET except that the server does not send response content, and describes HEAD as metadata about the selected representation. Those protocol properties do not themselves define Orgmetra service topology or application-specific replay authorization.

Use in ADR 0432:

- HTTP method semantics constrain transport behavior, but the composition layer does not maintain a second `retry_class` taxonomy;
- positive automatic replay of an Orgmetra operation requires the exact released owner operation contract to make that attempted replay safe under the observed request state;
- POST/mutation replay is not made safe by either shared edge transport or product composition; where replay is supported, the released owner service's exact `Idempotency-Key`/replay contract remains authoritative;
- an ambiguous failure after a potentially committed non-replay-safe mutation does not justify a fresh mutation attempt; and
- because HEAD is GET without response content for the same selected-resource semantics, Orgmetra collision ownership treats GET and HEAD as one effective selected-resource authority and rejects overlapping routes that split those methods across different owners. The declared route method set remains exact contract material; HEAD is not implicitly added to every GET route.

Not established by this source:

- Orgmetra semantic command digests, first-commit replay, optimistic-concurrency, retry admission, employment-fact idempotency semantics, or which bounded context owns a route. Those remain Orgmetra owner-domain and product-composition evidence.

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
- the product-composition inventory remains an admitted-operation catalogue, not a monolithic copied domain schema;
- route-path authority must be deterministic so overlapping templates cannot silently compete for one concrete request under the same effective method authority; the Orgmetra GET/HEAD equivalence used for collision ownership comes from RFC 9110 rather than OpenAPI itself; and
- a missing or incompatible owner contract leaves a route unavailable.

Not established by this source:

- semantic compatibility of two Orgmetra service releases, retry/replay safety, buyer readiness, deployment fitness, or immutable generation identity. Those require executable owner/consumer conformance evidence.

## Repository-owner capability evidence

These facts are not normative standards. They constrain architecture because CWL requires consumers to respect the released owner's actual supported contract rather than infer capability from repository existence.

### Orgmetra protected truth

On 2026-09-21:

- protected authority was `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`;
- protected `ARCHITECTURE.md` documented a buyer-facing Orgmetra Gateway and assigned API aggregation, tenant context, purpose-bound authorization, idempotency and event-envelope handling to the runtime layer;
- protected `docs/API_CONTRACT.md` documented pre-handler Keyverse OIDC validation at that boundary;
- protected People and Job Analysis HTTP code exposed injected `TokenAuthenticator` / `AuthenticatedPrincipal` ports rather than a released Keyverse verifier/ACL implementation; and
- the protected executable repository still had no supported deployable application that composes independently versioned owner APIs into that buyer-facing boundary.

Those protected responsibilities are therefore design obligations, not proof that one executable gateway currently exists.

### Draft executable canary #434

Draft PR #434 is the first bounded implementation slice under #432. It is intentionally stacked on the active Foundation owner #340 and therefore is not protected truth or hosted current-head gate evidence.

Current exact canary authority is `bdedbda008746ecfac39895b16537c2c99a63165`, 41 commits ahead / 0 behind #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`, with eight changed files confined to `services/product-composition-api/**`.

Its current executable evidence corrects several mistakes found through test-first/self-review without promoting the Draft into architecture or shipped truth:

- the composition digest is derived from a deterministic canonical semantic route projection instead of accepting any caller-supplied 64-hex label;
- a release locator must identify one exact `ContextualWisdomLab/<repository>/releases/tag/<version>` coordinate bound to the recorded release version;
- overlapping path templates are rejected across different owners when their effective method authorities overlap; GET and HEAD form one selected-resource collision authority while the actually declared method set remains canonical route material;
- each logical `service://` upstream is bound to the exact released owner service identity;
- the route model contains no composition-local retry class, idempotency mode, or concurrency mode;
- `AdmissionReceipt` can be issued only by the canonical evaluator and its exact issued generation/config/admitted-route fields remain bound to that receipt within process-local closure state;
- semantically equivalent route tuple ordering produces deterministic admitted/unavailable receipt route-ID ordering;
- admission revalidates the current nested owner/route/generation/config evidence immediately before use; and
- a canonically constructed `CompositionGeneration` is bound to its original process-local `(schema_version, generation_id, config_sha256)` construction snapshot, so changing `generation_id` or coherently rewriting both route semantics and a matching digest cannot silently redefine the same generation.

The generation-construction rule is not derived from OpenAPI, OAuth, or HTTP standards. It is an Orgmetra evidence-integrity requirement induced by the product's own generation/activation/rollback semantics. A generation identifier is useful only if it continues to name the same configuration lineage. Re-running constructor invariants on a mutable-in-practice Python object graph was insufficient because a caller could make a rewritten graph internally self-consistent. The current process-local construction snapshot closes that executable canary path while deliberately **not** claiming durable tamper resistance or same-process arbitrary-code isolation.

The GET/HEAD collision rule is narrower in a different way: RFC 9110 supplies the selected-resource method semantics, while Orgmetra's decision that one bounded-context owner must retain that effective authority is a product-architecture invariant. The standard does not dictate Orgmetra service ownership.

The latest ordinary-forward executable sequences include:

- `f7175e36d32034581cf05758b64256c06e7a3ea5` -> `105fa9a584c5aa9865c86082664411f922a84492` -> `d3e24da90bbd4b2c5e44f7acfaeb15225eff08a0` for generation construction identity;
- `5bbd018750a49a2bfa4c28d62c1b091f493c77b2` -> `79279c211fd5912a30060991cb5054fac19daba1` -> `db251db2168bdea2e5af321e75952826a1f5a21b` for canonical receipt route ordering; and
- `34a598ad2c60cd00b8c51b3be5a8abfd3b5b377f` -> `8a1e8854bb8e7c7a712e83dc9ef1e593095ebdfe` -> `bdedbda008746ecfac39895b16537c2c99a63165` for GET/HEAD selected-resource ownership.

Earlier focused local figures on predecessor `cb32ba828...`—16 tests, 201/201 statements and 84/84 branches—are predecessor mechanism evidence only. Material source and test bytes changed afterward. Current exact `bdedbda...` has no PR-triggered hosted workflow run while stacked on #340, so no current-head 100% statement/branch/docstring/edge, Security, SAST or CodeQL GREEN is claimed.

Synthetic owner-release fixtures and process-local identity registries do not prove an actual owner release, Keyverse conformance, Orgmetra identity ACL, deployment/recovery, commercial latency, durable activation authority, protected integration, or immutable Orgmetra release.

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
- HR/identity/authorization/idempotency/concurrency/retry truth already has narrower owners that the composition layer must preserve.

A future implementation may deploy the composition application behind a release-qualified shared edge or behind another approved ingress. The product contract remains the same. If measurement shows an unacceptable extra hop, optimization occurs against the measured deployed path rather than by collapsing ownership and silently moving product semantics into a reverse proxy.

## Evidence discipline

A standards citation, repository file, open PR, architecture diagram, synthetic fixture, frozen dataclass, process-local identity registry, or local unit suite is not GREEN implementation evidence. Commercial acceptance still requires exact protected/released identities, current-head conformance/security tests, cryptographic identity verification, explicit ACL projection tests, immutable generation/activation/deployment evidence, fault injection, recovery/rollback evidence and realistic k6/E2E measurements across every actually deployed layer and the owner PostgreSQL path.