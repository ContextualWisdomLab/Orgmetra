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

`resolve_calibration_auxiliary_authority(...)` corroborates #407's purpose-limited calibration input without copying protected source attributes. It binds auxiliary authority and projection coordinates, scientific-use purpose, released owner contract, authorization receipt/interval, and scientific-use receipt/instant. Caller `used_at` must equal the owner-resolved scientific-use instant, and that instant must fall inside the owner-resolved authorization interval.

## Calibration benchmark authority

`resolve_calibration_benchmark_authority(...)` corroborates benchmark receipt/version/digest, released benchmark-owner contract, reference/release chronology, and append-only predecessor/successor correction lineage. The owner contract must already be released when the benchmark receipt becomes released evidence; a predecessor is authoritative only on its owner-resolved half-open interval.

## Typed calibration-adjustment authority

`resolve_calibration_adjustment_authority(...)` corroborates the exact released calibration receipt that produced a point-weight artifact. It binds the receipt/evidence version to purpose-limited auxiliary and benchmark digests, primary method, constraints, artifacts, construction time, and released owner contract. `fallback_applied` additionally requires the primary failure reason, immutable fallback rule, and actual fallback algorithm/version/configuration; `converged` rejects fallback-only evidence. Raw auxiliary values, benchmark totals, protected attributes, and row-level weights are excluded.

## Typed nonresponse-adjustment authority

`resolve_nonresponse_adjustment_authority(...)` corroborates the exact released disposition-aware nonresponse receipt. It binds receipt/evidence version, exact response/disposition receipt reference/version/digest, owner-resolved disposition release time, adjustment population, method/version/configuration, explicit ineligible/unknown/unavailable treatments, input/output weight artifacts, construction time, and released owner contract. The disposition input must already exist by adjustment construction and scientific use cannot precede the typed receipt's release. Response values, source attributes, protected attributes, and row-level weights are excluded.

## Trimming/bounding adjustment authority

`resolve_trimming_bounding_authority(...)` corroborates the exact released trimming or bounding receipt rather than trusting an adjustment-chain digest alone. It binds the typed receipt reference/digest/evidence version to the governed `weight_trimming_rule` reference/version, immutable rule configuration, exact affected-case occurrence-set digest and positive affected-case count, input/output weight-artifact transition, construction time and released owner-contract tuple. Input and output artifacts may not alias; release cannot precede construction or scientific use. Case identities and row-level weights are excluded from the projection.

This preserves the evidence needed to reproduce which governed trimming/bounding rule changed which case occurrence set without copying those cases into `workforce_validation`. PR #248 or a verified successor must later re-resolve the same tuple from released owner evidence.

## Weight-eligibility authority

`resolve_weight_eligibility_authority(...)` corroborates #407 RED #9 instead of treating an eligibility digest as sufficient authority. It binds the exact `weight_eligibility_receipt` reference/digest/evidence version to explicit `cross_sectional | longitudinal` scope, governed target-population and reference-duration coordinates, exact eligible-case set, exact point-weight artifact, construction time, released owner-contract tuple, and owner-resolved receipt release time. Cross-sectional and longitudinal eligibility are distinct authority states; a different population, duration, case set, or artifact cannot be silently reused. Person attributes and row-level weights are excluded.

## Base/design-weight authority

`resolve_base_weight_authority(...)` corroborates the base/design-weight derivation instead of accepting `base_weight_evidence_digest` as an opaque caller label. It binds an exact released base-weight evidence receipt to the source-universe and sampling-design receipt references/versions/digests, their release chronology, the sampled occurrence set, an immutable digest of the stage-wise selection-probability evidence, the positive selection-stage count, base-weight method/version, resulting base-weight artifact, construction time, and released owner contract.

The stage-wise probability values themselves stay with the sampling owner. `workforce_validation` receives only the evidence identity needed to prove which selection-probability set and sampled occurrence set produced the base artifact. Source and sampling evidence must already be released when the base weight is constructed, and scientific use cannot precede release of the base-weight evidence. This closes the remaining #407 gap where the final-weight receipt carried only a base-evidence digest and artifact identity without independently corroborating the sampling evidence needed to verify `1/π` or another controlled base-weight derivation.

## Final analysis-weight authority

`resolve_final_analysis_weight_authority(...)` corroborates the complete #407 point-estimation lineage rather than trusting only the final receipt digest carried by the point-weight/variance compatibility boundary. It binds the exact final analysis-weight receipt to the estimand, target population, analysis unit/window/reference duration, eligible and analytic-case sets, owner-resolved source-universe and sampling-design receipt references/versions/digests, base-weight method/evidence/artifact, ordered typed adjustment chain, final point-weight artifact, weight-eligibility receipt, analytic-case count, append-only correction lineage, construction/release chronology, and released owner contract.

The ordered adjustment chain is immutable and contiguous: each transform must consume the preceding artifact, material transforms may not be no-ops, and known nonresponse/calibration/raking/poststratification/trimming/bounding/winsorization codes require their specialized receipt kind. Source/sampling references are owner-corroborated coordinates layered over the digest-only scientific leaf, so a caller cannot turn an opaque digest into a floating source/design version. The separate base-weight authority additionally resolves the stage-wise selection-probability evidence behind the base artifact. No row-level weights, case identities, protected calibration values, or foreign tables cross this boundary.

## Point-weight / variance authority

`resolve_weight_variance_authority(...)` corroborates released #405 sampling evidence, final analysis-weight receipt, analytic-case occurrence set, weight-eligibility receipt digest, correction sequence, final point-weight artifact, separate #406 variance-design evidence, variance method/evidence semantics, and released owner contract. A variance receipt cannot alias the point-weight receipt, and approximation evidence cannot be represented as exact. The separate eligibility, base-weight, and final analysis-weight authorities supply the durable population/duration, selection-probability provenance, and complete ordered point-weight lineage behind those compatibility coordinates.

## Released validation-result authority

`resolve_validation_result_authority(...)` binds one immutable validation result to the exact `WeightVarianceCompatibilityReceipt`, final analysis-weight receipt, separate variance-design receipt, non-authorizing `verification_pending | not_verifiable` state, and released owner contract. Numerical convergence is not promoted to `verified` at this boundary.

## Released non-verifiability outcome

`resolve_validation_result_nonverifiability(...)` is the application repair for #407 RED #12. It represents required analysis-weight, weight/variance-compatibility, or variance-design evidence that is `missing | non_reproducible` without turning lookup failure into scientific GREEN. Missing evidence carries no fabricated identity; non-reproducible evidence retains the exact failed reference/digest. Every outcome binds a separate immutable verification-attempt receipt, released owner contract, and evaluation/release chronology. Effect estimates, row-level weights, replicate vectors, protected attributes, and foreign application data are excluded.

## Persistence state

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's migration history. It creates the `workforce_validation` schema and a deny-default `workforce_validation_role`, revokes public schema access, and intentionally creates or moves no application table yet.

The schema owner is NOLOGIN and is not a runtime isolation control. PostgreSQL role-level `search_path` defaults are applied at login and are not re-applied by `SET ROLE`. A durable runtime adapter therefore needs a distinct least-privilege runtime role, schema-qualified relations, and explicit function-level `search_path` for any future `SECURITY DEFINER` function.

Protected foundation migrations still hold validity-study relations in the legacy foundation schema. PR #248 or a verified successor owns forward owner-schema adoption after this application owner reaches normal protected integration. It must preserve valid persistence/FK/RLS/ACL evidence and implement durable released-evidence ports for calibration auxiliary, calibration benchmark, typed calibration adjustment, typed nonresponse adjustment, trimming/bounding adjustment, weight eligibility, base/design-weight provenance, complete final analysis-weight lineage, point-weight/variance compatibility, validation-result binding, and validation-result non-verifiability.

## Test contract

The service is admitted to the canonical Foundation quality workflow with a 100% owned statement and branch threshold:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

`tests/test_workforce_validation_owner_schema_postgres.sh` separately executes the service-local migration against pinned PostgreSQL 16.14 and checks deny-default owner-role/schema behavior, actual `SET ROLE` search-path behavior, PUBLIC privileges, and absence of application relations in the bootstrap schema.

Scientific-authority tests cover authorization-before-owner-read, static port validation, malformed references/digests/versions/timestamps, exact owner-coordinate matching, UUID detachment/alias attacks, structural immutability, non-public view issuance, benchmark correction chronology, typed calibration fallback provenance, typed nonresponse disposition/treatment provenance and chronology, trimming/bounding rule and affected-case provenance, cross-sectional/longitudinal weight eligibility, stage-wise base/design-weight provenance, complete estimand/source/base-weight/ordered-adjustment/final-artifact lineage, point/variance compatibility, validation-result binding, and explicit missing/non-reproducible result evidence.

These source contracts are not terminal acceptance by themselves. The PR remains Draft until the exact current head executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and normal independent review/governance requirements are satisfied. Only protected/released owner evidence may be consumed as durable scientific authority.
