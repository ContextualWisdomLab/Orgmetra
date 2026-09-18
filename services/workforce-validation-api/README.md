# Orgmetra Workforce Validation API

This package is the canonical application boundary for the `workforce_validation` bounded context. It owns purpose-bound validation-study reads and scientific-evidence corroboration without copying People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, TEPP, or another bounded context's application tables.

Foreign domain truth crosses this boundary only through released/versioned contracts, opaque references, immutable evidence digests, and owner ports. Mutable `validity-analysis` source is not a runtime or source dependency of this service.

## Boundary invariants

- Keyverse identity is consumed as structurally immutable authenticated identity attributes, never credentials.
- Authorization is evaluated before an owner read.
- Repository capabilities are checked with inert static lookup; inherited Protocol placeholders and executable descriptors are not accepted as owner implementations.
- Tenant/study UUID identities are detached to exact integer payloads and reconstructed at public boundaries so retained UUID aliases cannot rewrite accepted authority.
- Owner evidence is reconstructed into exact tuple-backed records before comparison or projection.
- Returned views are field-minimized corroborating data. Their public constructors fail closed, and a view is not a reusable authorization credential.
- Cross-context SQL, mutable branch dependencies, row-level statistical weights, replicate vectors, protected attributes, and foreign application-table values do not cross this application boundary.

## Validity-study registry

`read_validity_study(...)` authorizes the exact tenant/study/purpose/operation/field request, then reads through `ValidityStudyReadPort`. Persisted registry evidence is reconstructed before tenant/study validation and only authorized fields are returned.

`ValidityStudyView` is a minimized projection. Downstream consequential actions must perform their own purpose-bound authorization and authoritative re-resolution.

## Calibration auxiliary authority

`resolve_calibration_auxiliary_authority(...)` corroborates #407's purpose-limited calibration input without copying protected source attributes. It binds auxiliary authority and projection coordinates, scientific-use purpose, released owner contract, authorization receipt/interval, and scientific-use receipt/instant. The governing owner-contract release instant is owner-resolved evidence rather than a caller coordinate, must be timezone-aware, and must be no later than `authorized_from`; this prevents a later contract from retroactively creating an earlier scientific-use authorization interval. Caller `used_at` must equal the owner-resolved scientific-use instant, and that instant must fall inside the owner-resolved authorization interval.

## Calibration benchmark authority

`resolve_calibration_benchmark_authority(...)` corroborates benchmark receipt/version/digest, released benchmark-owner contract, reference/release chronology, and append-only predecessor/successor correction lineage. The owner contract must already be released when the benchmark receipt becomes released evidence; a predecessor is authoritative only on its owner-resolved half-open interval `[released_at, superseded_at)`. When a successor exists, its released instant must equal the predecessor cutover exactly, so two released benchmark receipts cannot overlap in authority and no authority gap can appear between them.

## Typed calibration-adjustment authority

`resolve_calibration_adjustment_authority(...)` corroborates the exact released calibration receipt that produced a point-weight artifact. It binds the receipt/evidence version to the exact target-population digest and analysis-window reference, scientific auxiliary-authority reference, auxiliary projection reference/version/digest, scientific-use purpose reference/digest, auxiliary owner-contract reference/version/digest, authorization and scientific-use receipt references/digests plus scientific-use instant, benchmark receipt reference/version/digest, benchmark owner-contract reference/version/digest plus benchmark reference instant, primary method, constraints, artifacts, construction time, and the released application owner contract. `fallback_applied` additionally requires the primary failure reason, immutable fallback rule, and actual fallback algorithm/version/configuration; `converged` rejects fallback-only evidence. Raw auxiliary values, benchmark totals, protected attributes, and row-level weights are excluded.

The supporting auxiliary-use and benchmark-reference instants are caller-known receipt coordinates committed by the scientific calibration receipt and may not postdate calibration construction. The application owner-contract release instant is canonical owner evidence, not a resolver request coordinate. It must be timezone-aware and no later than the calibration receipt release. A contract may legitimately be released after adjustment construction but before receipt release, while a later contract cannot retroactively authorize an already released calibration receipt.

The ordinary typed-calibration record also carries an optional owner-resolved `superseded_at`. It is not a caller lookup coordinate and is not projected as reusable downstream authority. Scientific use is valid only on `[released_at, superseded_at)`: historical use before cutover remains reproducible and use at or after cutover fails closed.

## Calibration-adjustment supersession authority

`resolve_calibration_adjustment_supersession_authority(...)` proves the append-only correction edge behind typed-calibration currentness. An ordinary `superseded_at` alone is not enough to prove which immutable receipt ended the predecessor interval. A correction therefore requires one complete successor calibration receipt reference/digest/evidence-version/release tuple.

The successor must identify new immutable receipt evidence, remain on the governed v1 contract, be released after its predecessor, and satisfy `successor_released_at == superseded_at`. Successor coordinates are owner-resolved and omitted from the minimized current-receipt view. Durable persistence must make the ordinary calibration projection's cutover and the explicit successor edge agree on the same atomic correction instant; mutable current rows and caller timestamps are not correction authority.

## Typed nonresponse-adjustment authority

`resolve_nonresponse_adjustment_authority(...)` corroborates the exact released disposition-aware nonresponse receipt. It binds receipt/evidence version, exact response/disposition receipt reference/version/digest, owner-resolved disposition release time, adjustment population, method/version/configuration, explicit ineligible/unknown/unavailable treatments, input/output weight artifacts, construction time, and released owner contract. The disposition input must already exist by adjustment construction and scientific use cannot precede the typed receipt's release. Response values, source attributes, protected attributes, and row-level weights are excluded.

The owner-contract release instant and optional exclusive nonresponse cutover are canonical owner evidence rather than caller lookup coordinates. The ordinary resolver enforces `[released_at, superseded_at)`, so a corrected disposition, adjustment population, treatment rule, or weight-artifact transition cannot leave an older receipt apparently current.

## Nonresponse-adjustment supersession authority

`resolve_nonresponse_adjustment_supersession_authority(...)` binds the current nonresponse receipt and owner contract to release chronology and, when corrected, requires one complete successor receipt reference/digest/evidence-version/release tuple. The successor must identify new immutable evidence on the governed v1 contract, be released after its predecessor, and satisfy `successor_released_at == superseded_at`. Durable persistence must cross-check the ordinary nonresponse cutover against this explicit edge.

## Trimming/bounding adjustment authority

`resolve_trimming_bounding_authority(...)` corroborates the exact released trimming or bounding receipt rather than trusting an adjustment-chain digest alone. It binds the typed receipt reference/digest/evidence version to the governed `weight_trimming_rule` reference/version, immutable rule configuration, exact affected-case occurrence-set digest and positive affected-case count, input/output weight-artifact transition, construction time and released owner-contract tuple. Input and output artifacts may not alias; release cannot precede construction or scientific use. Case identities and row-level weights are excluded from the projection.

The governing owner-contract release instant and optional exclusive trimming/bounding cutover are owner-resolved evidence and never caller lookup coordinates. The ordinary resolver enforces `[released_at, superseded_at)`.

## Trimming/bounding supersession authority

`resolve_trimming_bounding_supersession_authority(...)` supplies the explicit correction edge for typed trimming/bounding receipts. A corrected predecessor requires one complete new successor receipt reference/digest/evidence-version/release tuple, with successor release exactly at the predecessor's `superseded_at`. Successor coordinates remain internal owner evidence.

## Weight-eligibility authority

`resolve_weight_eligibility_authority(...)` binds the exact `weight_eligibility_receipt` reference/digest/evidence version to explicit `cross_sectional | longitudinal` scope, governed target-population and reference-duration coordinates, exact eligible-case set, exact point-weight artifact, construction time, released owner-contract tuple, and owner-resolved receipt release time. The optional exclusive cutover is owner-resolved and the resolver enforces `[released_at, superseded_at)`.

## Weight-eligibility supersession authority

`resolve_weight_eligibility_supersession_authority(...)` proves which immutable successor ended an eligibility receipt's authority. A correction requires a complete successor receipt reference/digest/evidence version/release instant; it must identify new evidence and be released exactly at the predecessor cutover. The durable adapter must make the ordinary eligibility projection's cutover agree with this graph rather than derive currentness from a mutable row or caller timestamp.

## Base/design-weight authority

`resolve_base_weight_authority(...)` corroborates the base/design-weight derivation instead of accepting `base_weight_evidence_digest` as an opaque caller label. It binds an exact released base-weight evidence receipt to source-universe and sampling-design receipt references/versions/digests, their release chronology, the sampled occurrence set, stage-wise selection-probability evidence digest and stage count, base-weight method/version, resulting artifact, construction time, and released owner contract.

Stage-wise probability values stay with the sampling owner. Source-universe, sampling-design and owner-contract release instants are owner-resolved evidence rather than caller coordinates. Source and sampling evidence must already be released when the base weight is constructed; the owner contract must be released no later than the base-weight evidence receipt. The owner read is keyed by the complete caller-known reproducibility tuple rather than a partial receipt/source/design prefix.

## Final analysis-weight authority

`resolve_final_analysis_weight_authority(...)` corroborates the complete #407 point-estimation lineage. It binds the exact final analysis-weight receipt to the estimand, target population, analysis unit/window/reference duration, eligible and analytic-case sets, owner-resolved source-universe and sampling-design evidence, base-weight method/evidence/artifact, ordered typed adjustment chain, final point-weight artifact, weight-eligibility receipt, analytic-case count, append-only correction lineage, construction/release chronology, and released owner contract.

The owner read is keyed by the complete caller-known reproducibility tuple. Owner-contract release, final-weight release and supersession instants remain owner-resolved chronology. The ordered adjustment chain is immutable and contiguous; known nonresponse/calibration/raking/poststratification/trimming/bounding/winsorization codes require their specialized receipt kind. Scientific use is valid only on `[released_at, superseded_at)`.

## Final analysis-weight supersession authority

`resolve_final_weight_supersession_authority(...)` preserves predecessor release, exclusive supersession and complete released successor coordinates. The successor must have a new receipt reference and digest, advance correction sequence exactly by one, be released after its predecessor, and be released exactly at the predecessor cutover. Successor coordinates are omitted from the downstream view.

## Point-weight / variance authority

`resolve_weight_variance_authority(...)` corroborates released sampling evidence, final analysis-weight receipt, analytic-case occurrence set, weight-eligibility receipt, correction sequence, final point-weight artifact, separate variance-design evidence, variance method/evidence semantics, and released owner contract. A variance receipt cannot alias the point-weight receipt, and approximation evidence cannot be represented as exact. The owner read is keyed by the complete compatibility tuple.

The binding resolves owner-contract release and optional exclusive supersession from canonical owner evidence and enforces `[released_at, superseded_at)`. This prevents corrected point-weight or variance-design lineage from leaving an older compatibility binding apparently current.

## Released validation-result authority

`resolve_validation_result_authority(...)` binds one immutable validation result to the exact point-weight/variance compatibility receipt, final analysis-weight receipt, separate variance-design receipt, non-authorizing `verification_pending | not_verifiable` state, and released owner contract. Owner-contract release and optional exclusive cutover are canonical owner chronology. Historical reads before cutover remain reproducible; use at or after cutover fails closed.

## Validation-result supersession authority

`resolve_validation_result_supersession_authority(...)` proves the released predecessor/successor result edge. A successor must use a new result reference and digest, advance correction sequence exactly by one, be released after its predecessor, and be released exactly at the predecessor cutover. Caller timestamps and mutable result rows do not establish correction authority.

## Released non-verifiability outcome

`resolve_validation_result_nonverifiability(...)` represents required analysis-weight, weight/variance-compatibility, or variance-design evidence that is `missing | non_reproducible` without turning lookup failure into scientific GREEN. Missing evidence carries no fabricated reference, digest, or release timestamp. Non-reproducible evidence retains the exact failed reference/digest and owner-resolved release instant; the failed evidence must already have been released when the verification attempt is evaluated.

The immutable `verification_attempt_reference` and `verification_attempt_digest` are part of the resolver and owner-read lookup identity. Verification-attempt release, governing owner-contract release and optional exclusive `superseded_at` remain owner-resolved chronology. The immutable attempt receipt must satisfy `evaluated_at <= verification_attempt_released_at <= released_at`, and the ordinary resolver accepts the released negative outcome only on `[released_at, superseded_at)`.

## Persistence state

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's migration history. It creates the `workforce_validation` schema and a deny-default `workforce_validation_role`, revokes public schema access, and intentionally creates or moves no application table yet.

The schema owner is NOLOGIN and is not a runtime isolation control. PostgreSQL role-level `search_path` defaults are applied at login and are not re-applied by `SET ROLE`. A durable runtime adapter therefore needs a distinct least-privilege runtime role, schema-qualified relations, and explicit function-level `search_path` for any future `SECURITY DEFINER` function.

Protected foundation migrations still hold validity-study relations in the legacy foundation schema. PR #248 or a verified successor owns forward owner-schema adoption after this application owner reaches normal protected integration. It must preserve valid persistence/FK/RLS/ACL evidence and implement durable released-evidence ports for all **seventeen** current application-owner families: calibration auxiliary, calibration benchmark, typed calibration adjustment, calibration-adjustment supersession, typed nonresponse adjustment, nonresponse-adjustment supersession, trimming/bounding adjustment, trimming/bounding supersession, weight eligibility, weight-eligibility supersession, base/design-weight provenance, complete final analysis-weight lineage, final-weight supersession, point-weight/variance compatibility, validation-result binding, validation-result supersession, and validation-result non-verifiability.

The typed-calibration adapter must exact-key the complete target-population/window and auxiliary/benchmark/generating-method/artifact/application-owner tuple. Calibration, eligibility, nonresponse and trimming/bounding ordinary cutovers must agree with their explicit successor graph on one atomic correction instant: `predecessor.superseded_at == successor.released_at`. Calibration-benchmark, final-weight and validation-result correction adapters have the same atomic release-at-cutover invariant. Base-weight and final-analysis-weight persistence must select evidence by their complete caller-known reproducibility tuples. Non-verifiability persistence must key the exact immutable verification-attempt reference/digest and preserve failed-evidence and attempt-release chronology. No durable adapter may infer currentness from mutable current rows or caller-supplied timestamps.

## Test contract

The service is admitted to the canonical Foundation quality workflow with a 100% owned statement and branch threshold:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

`tests/test_workforce_validation_owner_schema_postgres.sh` separately executes the service-local migration against pinned PostgreSQL 16.14 and checks deny-default owner-role/schema behavior, actual `SET ROLE` search-path behavior, PUBLIC privileges, and absence of application relations in the bootstrap schema.

Scientific-authority tests cover authorization-before-owner-read, static port validation, malformed references/digests/versions/timestamps, exact owner-coordinate matching, UUID detachment/alias attacks, structural immutability, non-public view issuance, calibration-auxiliary owner-contract chronology, benchmark correction chronology, complete typed-calibration context and fallback provenance, **typed-calibration owner-resolved currentness and explicit predecessor/successor correction authority with exact release-at-cutover**, typed nonresponse currentness and supersession, trimming/bounding currentness and supersession, eligibility currentness and supersession, complete base/design-weight lookup coordinates, complete final-analysis-weight lineage/currentness/supersession, complete point-weight/variance compatibility/currentness, validation-result currentness/supersession, and explicit missing/non-reproducible evidence including exact verification-attempt identity and chronology.

These source contracts are not terminal acceptance by themselves. The PR remains Draft until the exact current head executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and normal independent review/governance requirements are satisfied. Only protected/released owner evidence may be consumed as durable scientific authority.
