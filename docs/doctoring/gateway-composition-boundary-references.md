# Gateway composition boundary references

Verification date: 2026-09-21

Scope: primary standards and authoritative specifications used by ADR 0432. This file records what each source supports and what it does **not** prove for Orgmetra. It is not evidence that a gateway implementation, owner API, shared edge runtime, identity adapter, or commercial latency target has passed.

## Source-to-decision traceability

### OAuth and OpenID Connect

**OpenID Foundation. (2023). _OpenID Connect Core 1.0 incorporating errata set 2_. https://openid.net/specs/openid-connect-core-1_0.html**

The OpenID Foundation approved the second errata set in December 2023. OpenID Connect remains the published authentication/claims contract referenced by protected Orgmetra architecture. In 2025 the errata-set-2 Core specification was also published as ITU-T X.1285; that recognition does not change Keyverse/Orgmetra ownership.

Use in ADR 0432:

- Keyverse remains the identity provider;
- the gateway may validate the product-facing OIDC bearer token but does not become credential or identity authority;
- verified issuer/subject/audience and claim coordinates still require explicit Orgmetra consumer/ACL handling before they become Orgmetra tenant/actor/operation-capability coordinates; and
- downstream domain authorization remains separate from authentication and coarse scope checks.

Not established by this source:

- that Orgmetra's current Keyverse integration is conformant;
- that a Keyverse `org`, `workspace`, `role`, or `sub` value can be cast directly into an Orgmetra HRIS identifier;
- that every valid OIDC subject is eligible for durable RP/Person correlation;
- that forwarding any particular token/context representation between gateway and owner services is safe; or
- that a Keyverse or shared-gateway release exists.

The durable-correlation distinction is therefore owned by Keyverse contract work rather than inferred from generic OIDC syntax. Existing Keyverse #155 owns subject-assertion trust semantics for durable RP binding. The broader Keyverse #158 release envelope must adopt/reuse those semantics, or demonstrate complete verified succession, rather than creating a second subject-trust truth. On the Orgmetra side, #295/#297 own durable subject-binding/consumer ACL behavior and #65 owns purpose-bound authorization runtime integrity. ADR 0432 composes these owners; it does not replace them.

**Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). _Best current practice for OAuth 2.0 security_ (BCP 240, RFC 9700). RFC Editor. https://www.rfc-editor.org/rfc/rfc9700.html**

RFC 9700 is the IETF Best Current Practice for OAuth 2.0 security as of this verification date. It updates security guidance associated with RFCs 6749, 6750, and 6819 and rejects several insecure historical patterns.

Use in ADR 0432:

- bearer-token handling at the product edge is a security boundary, not generic header forwarding;
- redirect/browser behavior, if introduced, must follow explicit secure flow rules instead of proxy defaults;
- authentication material and key-rotation failures must fail closed rather than fall back to weaker legacy handling; and
- an identity backend outage is not permission for anonymous or decoded-only fallback.

Not established by this source:

- Orgmetra-specific tenant, actor, business-purpose, employment-policy, resource authorization, durable Person binding, or Keyverse-to-Orgmetra ACL semantics.

### HTTP semantics, retries, and errors

**Fielding, R., Nottingham, M., & Reschke, J. (2022). _HTTP semantics_ (RFC 9110). RFC Editor. https://www.rfc-editor.org/rfc/rfc9110.html**

RFC 9110 Section 9.2.2 defines HTTP method idempotency and explains why idempotent requests can be automatically retried after some communication failures.

Use in ADR 0432:

- transport retry policy distinguishes protocol-level idempotent methods from application commands;
- POST/mutation replay is not made safe merely by the gateway; replay requires the released owner contract's exact `Idempotency-Key` semantics; and
- an ambiguous failure after a potentially committed non-replay-safe mutation does not justify a fresh mutation attempt.

Not established by this source:

- Orgmetra's semantic command digest, first-commit replay, or employment-fact idempotency contract. Those remain owner-domain evidence.

**Nottingham, M., Wilde, E., & Dalal, S. (2023). _Problem details for HTTP APIs_ (RFC 9457). RFC Editor. https://www.rfc-editor.org/rfc/rfc9457.html**

RFC 9457 is the current IETF Standards Track Problem Details specification and obsoletes RFC 7807. Its security considerations warn against leaking sensitive implementation details in errors.

Use in ADR 0432:

- if an owner publishes RFC 9457 Problem Details, the gateway preserves the owner's status and problem identity rather than converting it to generic success;
- client-visible problem payloads must not expose stack dumps, credentials, internal topology, or restricted data; and
- error-format normalization is a versioned owner/product decision, not an implicit proxy behavior.

Not established by this source:

- that protected Orgmetra APIs already publish RFC 9457. Protected `docs/API_CONTRACT.md` currently shows a versioned Orgmetra error shape; canonical standardization, if chosen, belongs to the existing documentation/API owner path.

### API contract description

**OpenAPI Initiative. (2025). _OpenAPI Specification v3.2.0_. https://spec.openapis.org/oas/v3.2.0.html**

Protected Orgmetra documentation already uses OpenAPI 3.2.0 as its HTTP contract language.

Use in ADR 0432:

- route admission is tied to a released owner API contract/version and exact OpenAPI digest;
- the gateway composition inventory does not turn separately owned OpenAPI contracts into one monolithic domain schema; and
- missing or incompatible owner contracts keep a route unadmitted.

Not established by this source:

- semantic compatibility of two Orgmetra service releases. Compatibility requires executable consumer/provider conformance evidence.

## Repository evidence used with the standards

The standards above are combined with live repository evidence, not substituted for it.

On 2026-09-21:

- Orgmetra protected authority was `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`;
- protected `ARCHITECTURE.md` documented an Orgmetra Gateway;
- protected `docs/API_CONTRACT.md` documented pre-handler Keyverse OIDC validation at that gateway;
- protected People/Job Analysis service code exposed an injected `TokenAuthenticator` and `AuthenticatedPrincipal` contract, where the principal carries an Orgmetra tenant UUID, opaque actor reference, and explicit `orgmetra.*` operation scopes; no released Keyverse verifier/ACL implementation was present in that protected runtime path;
- the executable repository still lacked one supported deployable product composition boundary;
- `ContextualWisdomLab/pingora-gateway` protected authority was `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991`;
- its published GitHub Release inventory was empty;
- root PR #1 exact `38db1949354f5721dc0ecfeea395bcf958a64ace` remained Draft and recorded a PR-introduced `derivative 2.2.0` / RUSTSEC-2024-0388 supplier-admission RED plus incomplete current-head central CodeQL evidence;
- `ContextualWisdomLab/keyverse` protected authority was `main@7d9151cd2da260e118020c938c7358e2ee75d541` and its published GitHub Release inventory was empty;
- protected Keyverse constrained the OIDC relying-party mapper profile to one self-pinned audience plus optional canonical hardcoded `role`, `org`, and `workspace` claims rather than Orgmetra-specific HR claims;
- Keyverse #155 already owned the narrower durable-subject assertion/correlation trust semantics used by Orgmetra #297;
- Keyverse #158 was opened as the broader owner path for an immutable domain-neutral OIDC relying-party consumer release and was currentized to adopt/reuse #155 rather than create a parallel subject-trust contract;
- Orgmetra #295/#297 already owned the durable subject-binding/consumer ACL path, while #65 owned purpose-bound authorization runtime integrity; and
- ADR 0432 therefore leaves any gateway-specific runtime principal projection as composition work constrained by those existing owners, rather than silently allocating another identity/authorization source of truth.

Those repository facts are why ADR 0432 can select a **target** shared-owner architecture while still requiring both transport-runtime admission and identity-contract admission to fail closed today. They also prevent shortcuts in which Orgmetra broadens Keyverse claims merely to manufacture `tenant_record_id`, treats every `sub` as durably bindable, trusts mutable issuer configuration as production authority, or creates a second ACL/subject schema beside existing owner lanes.

## Evidence discipline

A standards citation is not GREEN implementation evidence. Commercial acceptance still requires exact protected/released identities, current-head conformance and security tests, cryptographic identity verification, explicit ACL projection tests, fault injection, deployment/recovery evidence, and realistic k6/E2E measurements against real deployable service boundaries. Synthetic fixtures may establish mechanism behavior but cannot by themselves establish buyer-path availability, latency, privacy, identity conformance, or scientific correctness.
