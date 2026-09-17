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

`resolve_calibration_auxiliary_authority(...)` corroborates #407's purpose-limited calibration input without copying protected source attributes. It binds:

- auxiliary authority reference;
- auxiliary projection reference/version/digest;
- scientific-use purpose reference/digest;
- released owner-contract reference/version/digest;
- authorization receipt reference/digest and owner-resolved authorization interval;
- scientific-use receipt reference/digest and owner-resolved scientific-use instant.

Caller `used_at` must equal the owner-resolved scientific-use instant, and that instant must fall inside the owner-resolved authorization interval.

## Calibration benchmark authority

`resolve_calibration_benchmark_authority(...)` corroborates the benchmark tuple used by a calibration receipt:

- benchmark receipt reference/version/digest;
- released benchmark-owner contract reference/version/digest;
- benchmark reference instant and owner-resolved release instants;
- append-only predecessor/successor correction lineage when a benchmark is superseded.

The owner contract must already be released when the benchmark receipt becomes released evidence. A successor must advance the version, identify new evidence, be released after its predecessor, and exist no later than the predecessor's supersession instant. A predecessor is authoritative only on its owner-resolved half-open interval `[benchmark_receipt_released_at, benchmark_receipt_superseded_at)`.

## Typed calibration-adjustment authority

`resolve_calibration_adjustment_authority(...)` corroborates the exact released calibration receipt that produced a point-weight artifact. It binds the receipt digest and evidence version to the purpose-limited auxiliary projection digest, benchmark receipt digest, primary algorithm/version, constraints, input/output weight artifact digests, construction time, and released owner-contract evidence.

For `termination_code="fallback_applied"`, owner evidence must additionally preserve the primary failure reason, immutable fallback-rule reference/digest, and the actual fallback calibration algorithm/version/configuration that produced the output weights. `converged` rejects all fallback-only coordinates. The two weight-artifact digests must differ, release cannot precede construction, and the receipt cannot authorize scientific use before its owner-resolved release. Auxiliary values, benchmark totals, protected attributes, and row-level weights are excluded from the projection.

This closes the application-owner side of #407 RED #7 without importing mutable `validity-analysis` source. It does not make caller-supplied leaf evidence self-authenticating; the durable adapter must re-resolve released typed calibration evidence from its owner.

## Point-weight / variance authority

`resolve_weight_variance_authority(...)` corroborates point-estimation and variance evidence without treating leaf-provided digests as owner authority. It binds:

- released #405 sampling receipt reference/version/digest;
- final analysis-weight receipt digest;
- exact analytic-case occurrence set;
- weight-eligibility receipt digest;
- integer correction sequence;
- final point-weight artifact digest;
- distinct #406 variance-design receipt reference/version/digest;
- controlled variance method/version, evidence mode, and exact/approximate semantics;
- released owner-contract reference/version/digest and owner-resolved release instant.

A variance receipt cannot alias the point-weight receipt, and an approximation cannot be represented as exact evidence.

## Released validation-result authority

`resolve_validation_result_authority(...)` binds one immutable validation result to the exact weight/variance evidence it claims to use. It requires:

- result reference/digest;
- exact `WeightVarianceCompatibilityReceipt` reference/digest;
- final analysis-weight receipt digest;
- separate variance-design receipt digest;
- non-authorizing `verification_pending | not_verifiable` state;
- released owner-contract reference/version/digest and owner-resolved release instant.

Result, compatibility, point-weight, and variance digests must be pairwise distinct. Numerical convergence cannot be promoted to `verified` at this boundary.

## Released non-verifiability outcome

`resolve_validation_result_nonverifiability(...)` is the application repair for #407 RED #12. The ordinary result-authority contract requires exact compatibility/point-weight/variance digests, so it cannot represent the case where required evidence itself is missing or cannot be reproduced. This separate contract makes that failure explicit and non-authorizing instead of allowing callers to treat lookup failure as scientific GREEN.

`ValidationResultNonVerifiabilityRecord` fixes `verification_status` to `not_verifiable` and records exactly one failed evidence family:

- `analysis_weight_receipt`;
- `weight_variance_compatibility_receipt`; or
- `variance_design_receipt`.

`failure_mode` is `missing` or `non_reproducible`.

For `missing`, failed-evidence reference/digest must both be absent; the service does not fabricate an opaque identity for evidence that does not exist. For `non_reproducible`, the exact typed failed-evidence reference and digest are required. Every released outcome additionally binds an immutable `validation_evidence_verification_attempt` reference/digest, released owner-contract reference/version/digest, `evaluated_at`, and `released_at`. Result, failed-evidence when present, verification-attempt, and owner-contract digests must be distinct. Evaluation may not occur after release, and the outcome cannot be consumed before release.

Authorization occurs before `ValidationResultNonVerifiabilityReadPort` resolution. Returned `ValidationResultNonVerifiabilityView` contains only the minimized reason/provenance tuple; effect estimates, uncertainty values, row-level weights, replicate vectors, protected attributes, and foreign application data are excluded.

This is still application-boundary corroboration, not durable scientific authority. A later owner persistence adapter must establish missing/non-reproducible evidence from released owner/verification-attempt evidence rather than from cross-context SQL, missing joins, or swallowed exceptions.

## Persistence state

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's migration history. It creates the `workforce_validation` schema and a deny-default `workforce_validation_role`, revokes public schema access, and intentionally creates or moves no application table yet.

The schema owner is NOLOGIN and is not a runtime isolation control. PostgreSQL role-level `search_path` defaults are applied at login and are not re-applied by `SET ROLE`. A durable runtime adapter therefore needs a distinct least-privilege runtime role, schema-qualified relations, and explicit function-level `search_path` for any future `SECURITY DEFINER` function.

Protected foundation migrations still hold validity-study relations in the legacy foundation schema. PR #248 or a verified successor owns forward owner-schema adoption after this application owner reaches normal protected integration. It must preserve valid persistence/FK/RLS/ACL evidence and implement durable released-evidence ports for calibration auxiliary, calibration benchmark, typed calibration adjustment, point-weight/variance, validation-result binding, and validation-result non-verifiability.

## Test contract

The service is admitted to the canonical Foundation quality workflow with a 100% owned statement and branch threshold:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

`tests/test_workforce_validation_owner_schema_postgres.sh` separately executes the service-local migration against pinned PostgreSQL 16.14 and checks deny-default owner-role/schema behavior, actual `SET ROLE` search-path behavior, PUBLIC privileges, and absence of application relations in the bootstrap schema.

Scientific-authority tests cover authorization-before-owner-read, static port validation, malformed references/digests/versions/timestamps, exact owner-coordinate matching, UUID detachment/alias attacks, structural immutability, non-public view issuance, benchmark correction chronology, typed calibration fallback generating-method provenance, point/variance evidence compatibility, validation-result binding, and explicit missing/non-reproducible result evidence.

These source contracts are not terminal acceptance by themselves. The PR remains Draft until the exact current head executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and normal independent review/governance requirements are satisfied. Only protected/released owner evidence may be consumed as durable scientific authority.
