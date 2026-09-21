# Gateway composition boundary traceability

Verification date: 2026-09-21

Related issue: #432

Related Proposed ADR: `docs/adr/0432-deployable-orgmetra-gateway-composition-boundary.md`

## Protected-truth RED

Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` documents one buyer-visible Orgmetra Gateway and assigns API aggregation plus pre-handler Keyverse authentication responsibility to that boundary. The protected executable repository still has no supported deployable product-composition application across independently versioned owner services. This document is design/acceptance traceability only and does not turn that RED into shipped capability.

Draft #434 is the first bounded executable canary under #432. It is stacked on #340 and remains unprotected, so it carries no deployment or release credit.

## Fresh owner evidence

### Shared edge runtime

`ContextualWisdomLab/pingora-gateway` protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` has no published immutable GitHub Release. Its generic v1 owner contract requires one upstream and excludes product route tables, user-selected destinations, credentials, retry counts, Keyverse identity, and product authentication/authorization. The pg-erd multi-route path is migration-bounded and explicitly not a generic product-policy language.

Two independent gates remain: the shared edge is unreleased/security-nonterminal, and even a future release of its current generic v1 contract would not implement Orgmetra multi-owner product composition.

### Identity and authorization

`ContextualWisdomLab/keyverse` protected `main@7d9151cd2da260e118020c938c7358e2ee75d541` has no published immutable consumer release. Keyverse #155 owns durable subject-trust semantics and #158 the broader immutable OIDC relying-party release envelope. Orgmetra #295/#297 own durable subject-to-Person binding/consumer ACL. Orgmetra #65 and domain owners retain purpose/resource authorization. Product composition may project one verified runtime principal but cannot become a second identity, Person-binding, or authorization authority.

### Executable product-composition canary

Draft #434 exact authority is `a98dd5f7ffd175e2a7b3b5ca61255420f2959f8b`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`, 77 ordinary-forward commits with 13 changed files, all confined to `services/product-composition-api/**`.

The current canary proves only structural admission invariants:

- exact owner release/OpenAPI/artifact/repository attribution and owner-bound logical upstream;
- one exact `OwnerApiRelease` per `service_id` per generation;
- deterministic configuration digest over canonical route material;
- invalid per-route and cross-route material rejected before configuration identity;
- URI dot-segment and repeated path-template-expression rejection;
- one exact OpenAPI template identity per parameter-name-independent path hierarchy;
- distinct methods may share the same exact template string when operation ownership is otherwise valid;
- same-owner concrete-before-template precedence is permitted only when the exact owner release and declared method set are the same;
- cross-owner concrete/template overlap and ambiguous two-templated overlap remain fail-closed;
- effective-method authority is separate from path matching, with GET/HEAD treated as one selected-resource collision authority while declared methods remain exact contract material;
- no composition-local retry/idempotency/concurrency taxonomy;
- canonical process-local `AdmissionReceipt` field binding/source-generation leasing and deterministic receipt ordering;
- use-time revalidation of owner/route/generation/config evidence; and
- process-local generation construction/live-lineage protection without claiming durable activation authority.

Production activation/rollback still needs immutable durable generation/configuration/deployment authority that rejects historical ID reassignment across process lifetimes.

## Latest executable finding and repair

The previous admission rule was too broad after correctly detecting path overlap: it rejected **every** same-effective-method concrete/template overlap, including a valid OpenAPI pattern owned by one service. OpenAPI Specification 3.2.1 Section 4.8.1 states that concrete non-templated paths are matched before templated counterparts; Section 4.8.2.1 illustrates `/pets/mine` taking precedence over `/pets/{petId}`.

A service therefore needs to be able to publish a deterministic pair such as `GET /v1/people/current` and `GET /v1/people/{person_record_id}` without composition rejecting its released API shape. That permission must not weaken ownership isolation or create framework-specific fallback semantics.

Ordinary-forward repair:

- `fd7e7c69105fa2850dc30dd43014592f1a753eaa` — adds a positive same-owner concrete/template precedence case, keeps cross-owner overlap negative, and adds a same-owner ambiguous-two-template negative case;
- `393cb561a1226529553baa6129378281cfba6f27` — admits concrete/template overlap only when both routes bind the same exact owner release and the same declared method tuple, while retaining every other effective-authority overlap as fail-closed; and
- `a98dd5f7ffd175e2a7b3b5ca61255420f2959f8b` — documents path-key identity, deterministic path matching, and HTTP method authority as three separate layers.

The same-method-set restriction prevents composition from inventing a template fallback when OpenAPI selects a concrete Path Item that does not declare the requested operation. A broader fallback model requires explicit released-owner conformance evidence.

The preceding OpenAPI path-key sequence remains `2b4f2211a2e332058bec31af11474d3937899855` -> `2c7bfcf75ec2d353d52ed86cbcd74dba5ddae3ea` -> `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`: same hierarchy with different placeholder names is one OpenAPI path identity independent of HTTP method.

Earlier focused local figures at predecessor `cb32ba828...` are predecessor evidence only; material source/test writes followed.

## Corrected context map

```mermaid
flowchart LR
    client[Orgmetra workspaces / API clients]
    edge[Released shared edge transport\noptional deployment layer]
    composition[Orgmetra product composition\ndeployable application adapter]
    keyverse[Keyverse released RP contract\n#155 semantics + #158 release]
    identity_acl[Orgmetra identity ACL\n#295/#297]
    authz[Purpose/resource authorization\n#65 + owner services]
    people[people_core]
    org[organization_core]
    jobs[job_architecture]
    talent[talent owners]
    perf[performance_management]
    assess[assessment_coordination]
    validation[workforce_validation]

    client --> edge
    edge --> composition
    client -. approved deployment without shared edge .-> composition
    composition -. verify released identity contract .-> keyverse
    composition --> identity_acl
    identity_acl --> authz
    authz --> people
    authz --> org
    authz --> jobs
    authz --> talent
    authz --> perf
    authz --> assess
    authz --> validation
```

The protected product label “Orgmetra Gateway” remains the buyer-facing boundary. Internally, generic edge transport and product composition have different owners. Composition is an application adapter, not an HR bounded context.

## Ownership matrix

| Concern | Owner | Composition role | Forbidden behavior |
|---|---|---|---|
| Generic network/proxy/TLS/drain | released shared-edge owner | consume supported released capability | copy mutable edge source or reinterpret single-upstream config as product routing |
| Product route/admission generation | Orgmetra #432 | bind reproducible admitted owner operations | reuse pg-erd migration policy; rewrite generation meaning; same-hierarchy path aliases; cross-owner concrete/template overlap; ambiguous templated overlap; split GET/HEAD authority; dot-segment aliases; repeated template expressions; split owner release identities |
| Identity issuer/profile | Keyverse | consume released RP verifier/profile | issue credentials or broaden Keyverse with HR claims |
| Durable subject trust | Keyverse #155 packaged by #158 | preserve released semantics | assume every syntactically valid `sub` is durably bindable |
| Durable subject-to-Person binding / ACL | Orgmetra #295/#297 | consume/revalidate evidence | mint Person truth in composition |
| Runtime actor/tenant projection | Orgmetra composition constrained by #295/#297 | map verified identity to request coordinates | implicit UUID cast or decoded-only trust |
| Purpose/resource authorization | Orgmetra #65 + domain owners | propagate exact context; coarse early denial only | make role/scope/purpose self-authorizing |
| Person/Employment/Assignment | People | route and preserve owner semantics | query/write People tables |
| Organization/Position | Organization | route and preserve owner semantics | query/write Organization tables |
| Job/FJA/KSAO | Job Architecture | route and preserve owner semantics | copy ontology/job schema |
| Talent/selection | owning Talent context | route and preserve owner semantics | make employment decisions |
| Assessment assignment intent | assessment coordination | route and preserve owner semantics | own execution/scoring/result truth |
| Scientific validity/fairness | Workforce Validation | preserve scientific states/errors | coerce pending/not-verifiable/non-convergence to success |
| Mutation idempotency/replay | owning domain service | forward owner coordinates and consume released replay semantics | invent a second replay taxonomy/state |
| Optimistic concurrency | owning domain service | forward exact owner coordinate | create composition-local version truth |
| Retry safety | released owner operation contract | deny by default unless exact owner contract authorizes replay | infer positive safety from method alone |

## Composition manifest semantics

A future executable `orgmetra_gateway_composition.v1` or equivalent identifies product/composition release provenance, schema/config/generation/activation identity, optional shared-edge release, Keyverse release/profile, Orgmetra identity-ACL version, stable route identity, exact path and method set, exact owner API/OpenAPI/artifact/release coordinates, owner-bound logical upstream, coarse capability, authoritative tenant/actor/purpose locations, and required/optional criticality.

Configuration digest is computed from canonical semantic projection. A generation identifier cannot be reassigned to a different semantic graph. One owner service maps to one exact owner release per generation. Owner idempotency/replay/concurrency/error/retry semantics are referenced through released owner evidence rather than copied.

Path concerns remain separate:

- **Path-key identity:** same-hierarchy templates with different placeholder names are one OpenAPI identity and cannot coexist.
- **Deterministic path matching:** a concrete path may coexist with its templated counterpart only inside the same exact owner release and same declared method set, preserving OpenAPI concrete-first selection without transferring ownership.
- **Ambiguity rejection:** overlapping templated paths with no defined winner remain fail-closed, including inside one owner release.
- **Operation authority:** after path matching is valid, effective-method collision is evaluated separately; GET/HEAD share one selected-resource collision authority.
- **Canonical URI/template syntax:** dot segments are rejected rather than normalized and a path cannot repeat one template expression.

A mutable branch, PR SHA, copied schema, floating tag, reachable endpoint, constructor success, self-consistent rewritten graph, split owner release identity, ambiguous path, or receipt-shaped value alone is not route authority.

## RED -> GREEN evidence map

| RED / risk | Required GREEN evidence | Owner lane |
|---|---|---|
| Gateway documented but no deployable composition | supported local + Kubernetes composition bound to immutable identities | #432 |
| shared edge unreleased or wrong contract | owner immutable release + supported capability | pingora-gateway owner |
| Keyverse RP consumer unreleased | released verifier/profile/fixtures + provenance/rollback | Keyverse #155/#158 |
| decoded/unverified identity trusted | issuer/audience/signature/algorithm/time/JWKS verification before projection | Keyverse + Orgmetra conformance |
| raw subject becomes Person truth | #295/#297 released binding evidence; forged/stale/cross-tenant fails closed | #295/#297 |
| scope/role bypasses purpose/resource auth | #65/domain-owner denial survives E2E | #65 + domain owner + composition |
| route lacks released owner API | missing/floating/incompatible owner contract rejected | #432/#434 |
| one service has multiple release identities | reject before admission and on use-time revalidation | #432/#434 |
| config digest is caller label | recompute deterministic digest from canonical route material | #434 |
| generation meaning rewritten | construction identity and use-time graph revalidation reject drift | #432/#434 + activation |
| same hierarchy uses different placeholder names under any methods | reject before hashing; distinct methods may reuse one exact template | #434 + HTTP E2E |
| same-owner concrete/template precedence is rejected | allow only same exact owner release + same method set; prove concrete route wins | #434 + HTTP E2E |
| concrete/template overlap crosses owner boundary | reject before hashing/admission | #434 + HTTP E2E |
| overlapping templated paths have no deterministic winner | reject even within one owner unless a future explicit released contract defines semantics | #434 + HTTP E2E |
| overlapping routes split one effective method authority including GET/HEAD | reject before activation; keep declared method sets unchanged | #434 + HTTP E2E |
| URI dot segment or repeated template expression admitted | reject before hashing/admission | #434 + HTTP E2E |
| logical upstream disagrees with owner release | owner-bound upstream invariant rejects route | #434 + HTTP E2E |
| receipt fields drift or stale source graph is trusted | canonical field binding plus current source-graph revalidation | #434; durable activation independent |
| tuple ordering changes receipt evidence | deterministic route-ID ordering | #434 + activation evidence |
| local retry/idempotency/concurrency taxonomy substitutes for owner truth | no local replay taxonomy; exact owner contract controls replay | #432/#434 + owner |
| route admission is presented as buyer readiness | readiness also requires identity/ACL/runtime/dependency evidence | #432 operability |
| contradictory tenant/actor/purpose coordinates | deterministic fail closed | composition + identity ACL |
| ambiguous post-commit failure duplicates mutation | no fresh mutation; only owner-declared same-key replay | fault E2E |
| owner denial/scientific non-success becomes success | preserve exact status/state/error identity | composition E2E |
| partial/stale configuration activates | generation-atomic activation against immutable identity | operability |
| cancellation/timeout leaks resources | bounded cleanup across deployed layers | runtime E2E |
| composition reaches peer DB | credentials/network/code prohibit cross-service SQL | security |
| latency benchmark bypasses deployed layer or DB | full deployed path measured | performance acceptance |

## Identity projection and replay invariants

#155 decides durable subject-correlation eligibility; #158 cannot silently broaden it. #295/#297 remain the durable subject-binding path. Verified Keyverse `sub` maps only to an opaque namespaced actor reference through a versioned ACL. `org`/`workspace` require explicit Orgmetra mapping. #65/domain owners still evaluate business purpose/resource. Missing verifier/JWKS/ACL/owner evidence is failure, never permissive fallback.

Product composition has no local replay truth. If an owner commits a mutation but the response is lost, same-key replay occurs only when the exact released owner operation contract authorizes it; the owner returns the original committed identity and composition preserves it. HTTP idempotency semantics constrain the protocol but do not prove application replay safety.

## Performance evidence

The measured buyer path is:

`k6/client -> [shared edge if deployed] -> Orgmetra composition -> owner HTTP -> PostgreSQL -> owner -> composition -> [edge] -> client`

For designated ordinary paths p95 <= 20 ms. Evidence records load shape, deployment identity, right-to-use dataset, PostgreSQL/schema/index/RLS state, auth/audit state, identity/ACL coordinates, composition release/config/generation identity, optional edge release, owner API/OpenAPI identity, hardware/runtime, and timestamps. Slow requests are not discarded, samples are not shrunk to pass, and auth/audit/database layers are not skipped.

## Deployment and recovery evidence

GREEN requires production-equivalent Podman/Colima boundaries, supported Kubernetes packaging, immutable artifact/image identities, no cross-schema composition credentials, separate liveness/config/identity/route/readiness signals, bounded drain, immutable generation activation/rollback with owner compatibility revalidation, and logs/metrics/traces that exclude credentials/restricted HR payloads and unbounded sensitive labels.

## Single-writer handoff

- #432 remains the executable product-composition gap owner; #434 is its bounded first slice.
- #433 owns this Proposed ADR/traceability/doctoring lane. This source is current through OpenAPI path-key identity **and** deterministic same-owner concrete-path precedence, plus earlier receipt, owner/upstream, release-coherence, use-time revalidation, generation identity, receipt ordering, GET/HEAD, URI dot-segment, and repeated-expression findings.
- #340 remains the Foundation prerequisite/owner; #434 remains stacked on it to avoid a parallel Foundation writer.
- #51 remains canonical writer for protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and manifest reconciliation after architecture admission.
- #100 remains sole writer for `docs/product-technical-gap-baseline.md`; `API-01` stays Planned while #434 is unprotected and non-deployable.
- Keyverse #155/#158, Orgmetra #295/#297/#65, domain API owners, and pingora-gateway retain their authority.

No source in this Proposed lane or Draft #434 grants protected integration, release, deployment, buyer-readiness, or performance credit.
