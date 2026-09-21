# Gateway composition boundary traceability

Verification date: 2026-09-22

Related issue: #432

Related Proposed ADR: `docs/adr/0432-deployable-orgmetra-gateway-composition-boundary.md`

## Protected-truth RED

Protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` documents one buyer-visible Orgmetra Gateway and assigns API aggregation plus pre-handler Keyverse authentication responsibility to that boundary. Protected `docs/API_CONTRACT.md`, `docs/TRD.md`, `schemas/openapi.yaml`, and Foundation validation retain OpenAPI 3.2.0. The protected executable repository still has no supported deployable product-composition application across independently versioned owner services. This document is design/acceptance traceability only and does not turn that RED into shipped capability.

Draft #434 is the first bounded executable canary under #432. It is stacked on #340 and remains unprotected, so it carries no deployment or release credit.

## Fresh owner evidence

### Shared edge runtime

`ContextualWisdomLab/pingora-gateway` protected `main@f8b4c99b8e5d3de79af1ff0c00c0c8fd63b52991` still has no published immutable GitHub Release. Its generic v1 owner contract requires one upstream and excludes product route tables, user-selected destinations, credentials, retry counts, Keyverse identity, and product authentication/authorization. The pg-erd multi-route path is migration-bounded and explicitly not a generic product-policy language.

Two independent gates remain: the shared edge is unreleased, and even a future release of its current generic v1 contract would not implement Orgmetra multi-owner product composition.

### Identity and authorization

`ContextualWisdomLab/keyverse` protected `main@7d9151cd2da260e118020c938c7358e2ee75d541` still has an empty GitHub Release inventory. Keyverse #155 owns durable subject-trust semantics and #158 the broader immutable OIDC relying-party release envelope. Orgmetra #295/#297 own durable subject-to-Person binding/consumer ACL. Orgmetra #65 and domain owners retain purpose/resource authorization. Product composition may project one verified runtime principal but cannot become a second identity, Person-binding, or authorization authority.

### Executable product-composition canary

Draft #434 exact authority is `9852fe6bf1b4cddf1b4710d2908cb42019a0ac86`, stacked on #340 exact `28f2bd28414e217f7e848ba86c0cfdbe97fd518f`, with 88 ordinary-forward commits / 14 changed files, all confined to `services/product-composition-api/**`.

The canary proves only structural admission invariants:

- exact owner release/OpenAPI/artifact/repository attribution and owner-bound logical upstream;
- one exact `OwnerApiRelease` per `service_id` per generation;
- one exact `OwnerApiRelease` per exact OpenAPI Path Item in the current product profile;
- deterministic configuration digest over canonical route material;
- invalid per-route and cross-route material rejected before configuration identity;
- URI dot-segment and repeated path-template-expression rejection;
- one exact OpenAPI template identity per parameter-name-independent path hierarchy;
- distinct methods may share the same exact template string only inside the same exact owner release;
- same-owner concrete-before-template precedence only for the same exact owner release and declared method set;
- cross-owner concrete/template overlap and ambiguous two-templated overlap fail closed;
- effective-method authority separate from path matching, with GET/HEAD treated as one selected-resource collision authority while declared methods remain exact contract material;
- no composition-local retry/idempotency/concurrency taxonomy;
- canonical process-local `AdmissionReceipt` field binding/source-generation leasing and deterministic receipt ordering;
- use-time revalidation of owner/route/generation/config evidence; and
- process-local generation construction/live-lineage protection without claiming durable activation authority.

Production activation/rollback still needs immutable durable generation/configuration/deployment authority that rejects historical ID reassignment across process lifetimes.

## Latest executable finding and repair

Fresh OpenAPI review found that the previous canary could admit one exact path under two distinct owner releases when their HTTP methods were disjoint. For example, `people_api` could own `GET /v1/people/{person_record_id}` while `job_analysis_api` owned `PUT` on the same exact path. Operation-method disjointness made the old exact-path branch continue before checking owner identity.

That state is not supportable by the current contract. An OpenAPI Path Item contains path-level `$ref`, `summary`, `description`, `servers`, and `parameters` in addition to operations. Path-level servers service all operations and Path Item parameters apply to all operations. The present composition contract does not define or test a cross-owner Path Item merge algorithm, so it cannot prove which released owner supplies those shared semantics. OpenAPI itself does not assign repository or bounded-context ownership; one-owner-per-Path-Item is the narrower Orgmetra fail-closed decision until an explicit released merge/conformance contract exists.

Ordinary-forward repair:

- `ede0b6d602d2160af6c3ae37253f9728ac4b1e08` — adds the regression that cross-owner GET/PUT on one exact path must fail while same-owner disjoint methods remain a positive control;
- `8b7b059d60bf732e1acc33dc63db2ad8d5cbb52a` — checks exact `OwnerApiRelease` equality before allowing disjoint methods on one exact path;
- `9852fe6bf1b4cddf1b4710d2908cb42019a0ac86` — documents Path Item shared-field semantics, the fail-closed ownership decision, and the evidence threshold for future broadening.

The preceding bounded-profile sequence remains `7a30ccd000c5e7b5a69e6f872277e7cf8fab2437` -> `a1b903cabc900b33ac4da36f3781bddc50cf57ee`. The deterministic path-selection sequence remains `fd7e7c69105fa2850dc30dd43014592f1a753eaa` -> `393cb561a1226529553baa6129378281cfba6f27` -> `a98dd5f7ffd175e2a7b3b5ca61255420f2959f8b`. Path-key identity remains `2b4f2211a2e332058bec31af11474d3937899855` -> `2c7bfcf75ec2d353d52ed86cbcd74dba5ddae3ea` -> `bf90bbfbc2eef88d57fd30286b41a86f483a3fa1`. Later test-only commits aligned stale assertions with the three-layer path model without weakening production admission.

Earlier focused local figures at predecessor `cb32ba828...` are predecessor evidence only; material source/test writes followed. Exact `9852fe6b...` currently has no PR-triggered hosted workflow evidence.

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
| Product route/admission generation | Orgmetra #432 | bind reproducible admitted owner operations | rewrite generation meaning; overclaim full OpenAPI support; split one exact Path Item across owner releases; same-hierarchy aliases; cross-owner/ambiguous path overlap; split GET/HEAD authority; dot-segment aliases; repeated expressions; split owner release identities |
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

A future executable `orgmetra_gateway_composition.v1` or equivalent identifies product/composition release provenance, schema/config/generation/activation identity, optional shared-edge release, Keyverse release/profile, Orgmetra identity-ACL version, stable route identity, exact product path and method set, exact owner API/OpenAPI/artifact/release coordinates, owner-bound logical upstream, coarse capability, authoritative tenant/actor/purpose locations, and required/optional criticality.

Configuration digest is computed from canonical semantic projection. A generation identifier cannot be reassigned to a different semantic graph. One owner service maps to one exact owner release per generation. One exact OpenAPI Path Item maps to one exact owner release in the current bounded profile. Owner idempotency/replay/concurrency/error/retry semantics are referenced through released owner evidence rather than copied.

Path concerns remain separate:

- **Supported profile:** protected product truth is OpenAPI 3.2.0, while the canary intentionally supports a fail-closed subset of OAS path/method forms.
- **Path-key identity:** same-hierarchy templates with different placeholder names are one OpenAPI identity and cannot coexist.
- **Path Item ownership:** distinct methods may reuse one exact path only under the same exact `OwnerApiRelease`; cross-owner Path Item composition requires a future released contract that reconciles path-level shared semantics.
- **Deterministic path matching:** a concrete path may coexist with its templated counterpart only inside the same exact owner release and same declared method set.
- **Ambiguity rejection:** overlapping templated paths with no defined winner remain fail-closed.
- **Operation authority:** after Path Item ownership and path matching are valid, effective-method collision is evaluated separately; GET/HEAD share one selected-resource collision authority.
- **Canonical URI/template syntax:** dot segments are rejected rather than normalized and a path cannot repeat one template expression.

A mutable branch, PR SHA, copied schema, floating tag, reachable endpoint, constructor success, self-consistent rewritten graph, split owner release identity, cross-owner exact Path Item, ambiguous path, unsupported method/path form, or receipt-shaped value alone is not route authority.

## RED -> GREEN evidence map

| RED / risk | Required GREEN evidence | Owner lane |
|---|---|---|
| Gateway documented but no deployable composition | supported local + Kubernetes composition bound to immutable identities | #432 |
| shared edge unreleased or wrong contract | owner immutable release + supported capability | pingora-gateway owner |
| Keyverse RP consumer unreleased | released verifier/profile/fixtures + provenance/rollback | Keyverse #155/#158 |
| decoded/unverified identity trusted | issuer/audience/signature/algorithm/time/JWKS verification before projection | Keyverse + Orgmetra conformance |
| raw subject becomes Person truth | #295/#297 released binding evidence; forged/stale/cross-tenant fails closed | #295/#297 |
| scope/role bypasses purpose/resource auth | #65/domain-owner denial survives E2E | #65 + domain owner + composition |
| route lacks released owner API/operation | missing/floating/incompatible owner contract or absent operation rejected | #432/#434 + owner conformance |
| one service has multiple release identities | reject before admission and on use-time revalidation | #432/#434 |
| one exact Path Item is split across owner releases | reject before configuration identity; broaden only with explicit released path-item merge/conformance evidence | #432/#433/#434 + owner conformance |
| config digest is caller label | recompute deterministic digest from canonical route material | #434 |
| generation meaning rewritten | construction identity and use-time graph revalidation reject drift | #432/#434 + activation |
| canary is presented as full OpenAPI 3.2 support | document/test bounded route profile; broaden only from released-owner evidence | #433/#434 |
| same hierarchy uses different placeholder names under any methods | reject before hashing; distinct methods may reuse one exact template only inside one owner release | #434 + HTTP E2E |
| same-owner concrete/template precedence is rejected | allow only same exact owner release + same method set; prove concrete route wins | #434 + HTTP E2E |
| concrete/template overlap crosses owner boundary | reject before hashing/admission | #434 + HTTP E2E |
| overlapping templated paths have no deterministic winner | reject unless a future explicit released contract defines semantics | #434 + HTTP E2E |
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
- #433 owns this Proposed ADR/traceability/doctoring lane. This source is current through the one-owner-per-Path-Item finding as well as prior bounded-profile, path identity/matching, receipt, owner/upstream, release-coherence, use-time revalidation, generation identity, receipt ordering, GET/HEAD, URI dot-segment, and repeated-expression findings.
- #340 remains the Foundation prerequisite/owner; #434 remains stacked on it to avoid a parallel Foundation writer.
- #51 remains canonical writer for protected ARCHITECTURE/TRD/API/SECURITY/THREAT_MODEL/TEST_STRATEGY/OPERABILITY/TRACEABILITY and manifest reconciliation after architecture admission.
- #100 remains sole writer for `docs/product-technical-gap-baseline.md`; `API-01` stays Planned while #434 is unprotected and non-deployable.
- Keyverse #155/#158, Orgmetra #295/#297/#65, domain API owners, and pingora-gateway retain their authority.

No source in this Proposed lane or Draft #434 grants protected integration, release, deployment, buyer-readiness, or performance credit.
