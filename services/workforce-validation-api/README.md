# Orgmetra Workforce Validation API

This package is the application boundary for the `workforce_validation` bounded context. The current slice exposes purpose-bound owner reads for the existing validity-study registry header, value-minimized scientific auxiliary-use authority, released calibration-benchmark authority, and point-weight/variance-design compatibility authority while establishing the context-local PostgreSQL ownership bootstrap.

It does **not** query People, Talent Acquisition, Performance Management, Job Architecture, Psychometrics Commons, fast-mlsirm, TEPP, or another bounded context's application tables. Those contexts remain separate owners. Exact foreign identifiers and immutable specialist/scientific evidence cross this boundary only through released/versioned contracts and owner ports.

## Current slice

`read_validity_study(...)`:

- accepts structurally immutable authenticated Keyverse identity attributes, not credentials;
- reconstructs and revalidates principal storage before building the access request, so exact tuple type alone is not treated as identity authority;
- requires both exact `UUID` outer type and exact built-in integer UUID payload before any sentinel/range comparison, so a forged exact UUID with executable internal storage is rejected without invoking caller-defined equality behavior;
- stores UUID identity evidence behind the tuple-backed principal/record/view as exact integer payloads and reconstructs fresh UUID objects at public boundaries, so a retained UUID reference cannot rewrite accepted tenant/study/criterion identity through `object.__setattr__`;
- preserves tenant/study authorization targets as immutable integer snapshots across the executable repository call, so a repository cannot make a foreign record self-consistent by mutating the UUID objects it receives;
- inertly verifies that the owner repository exposes a statically callable `read_validity_study` capability before authorization, without executing caller-controlled descriptors;
- evaluates tenant, purpose, operation, scope, resource, and requested fields before persistence;
- calls only a `ValidityStudyReadPort` owned by this context;
- reconstructs persisted registry scalars into structurally immutable owner evidence before target validation and output;
- returns only the fields authorized for the exact study record; UUID-valued projected fields are reconstituted fresh rather than exposing mutable internal UUID aliases;
- issues `ValidityStudyView` only from the authorized read path. Its public constructor fails closed, and the returned tuple-backed projection cannot be rewritten through ordinary assignment or `object.__setattr__`.

`ValidityStudyView` is a data projection, not a durable authorization credential or cryptographic capability. Downstream consequential actions must perform their own purpose-bound authorization and authoritative re-resolution rather than treating the Python runtime type as reusable authority. Low-level interpreter construction is outside the supported public API and is not accepted as proof that authorization occurred.

`resolve_calibration_auxiliary_authority(...)` is an executable owner-side slice for #407's durable scientific-evidence resolution gap. It does **not** import or copy the mutable validity-analysis implementation. Instead it defines the `workforce_validation` application contract that a later durable adapter must satisfy:

- authorize the exact tenant/study scientific read before invoking the owner port;
- carry only opaque projection/purpose/owner/authorization/scientific-use references, SHA-256 evidence digests, immutable projection/contract versions, the owner-resolved scientific-use instant, and authorization time bounds—never calibration source attributes, protected characteristics, benchmark values, or row-level weights;
- require the exact purpose-limited auxiliary projection reference/version/digest rather than allowing a projection identity to float behind a digest or reference alone;
- require a released-owner-contract reference/version and corroborating owner-contract digest rather than treating a caller-supplied version label as release authority;
- require an immutable scientific-use receipt digest in the lookup and reconstruct the corresponding owner record, so a caller cannot choose a convenient historical `used_at` merely to fit a stale authorization interval;
- require the caller's exact `used_at` coordinate to equal the owner-resolved `scientific_use_at`, while the record itself requires that instant to fall inside the owner-resolved authorization interval;
- resolve through one statically captured `CalibrationAuxiliaryAuthorityReadPort` capability and reject inherited Protocol placeholders or descriptors before authorization;
- reconstruct the returned evidence into an exact tuple-backed `CalibrationAuxiliaryAuthorityRecord` and require tenant, study, projection reference/version/digest, scientific purpose, released owner contract, authorization receipt, scientific-use receipt, and use time to match the requested coordinates;
- issue only a minimized `CalibrationAuxiliaryAuthorityView`. The view is corroborating data, not a reusable authorization credential or proof that an arbitrary injected port is a production owner.

`resolve_calibration_benchmark_authority(...)` addresses #407 RED #5 at the canonical service boundary. The scientific leaf carries benchmark receipt reference/version/digest, released benchmark-owner contract reference/version/digest, and benchmark reference time; this resolver requires an owner port to corroborate those exact coordinates rather than accepting the leaf tuple as authority. It:

- authorizes the exact tenant/study read before any owner resolution and rejects inherited Protocol placeholders or descriptors as concrete repository capabilities;
- verifies the calibration-benchmark receipt and its released owner contract through opaque references, positive versions, SHA-256 digests, and the exact benchmark reference instant;
- obtains `benchmark_receipt_released_at` and `owner_contract_released_at` from owner evidence rather than from the caller, and rejects scientific use that predates either release or the benchmark reference instant;
- requires the referenced owner contract to have been released no later than the benchmark receipt itself, so a receipt cannot retroactively claim authority from a contract that did not yet exist when the receipt became released evidence;
- resolves append-only benchmark correction lineage from the owner: a superseded receipt carries a complete successor receipt reference/version/digest plus its owner-resolved release instant, the successor version must advance, and the successor digest must identify new evidence;
- requires the successor receipt to be released after its predecessor and no later than the predecessor's supersession instant, so correction lineage cannot point to unavailable future evidence or reverse version chronology;
- treats each benchmark receipt as authoritative only on its owner-resolved half-open interval `[benchmark_receipt_released_at, benchmark_receipt_superseded_at)`. Historical use before a later correction remains reproducible, while use at or after supersession fails closed;
- keeps supersession/successor coordinates inside the authority check rather than expanding the public projection. The caller receives only the minimized benchmark evidence it requested, not correction-ledger internals;
- reconstructs returned evidence into an exact tuple-backed `CalibrationBenchmarkAuthorityRecord` and fails closed on any tenant, study, receipt, owner-contract, digest, version, or reference-time mismatch;
- returns only a minimized `CalibrationBenchmarkAuthorityView`; benchmark totals, protected auxiliary values, row-level weights, and foreign application-table values do not cross this boundary.

`resolve_weight_variance_authority(...)` closes a separate #406/#407 application false-GREEN: a scientific leaf can prove internally that a point-weight receipt and variance receipt have compatible digests, yet a durable service must not treat those caller-supplied coordinates as owner authority. This resolver therefore:

- authorizes the exact tenant/study scientific read before invoking one statically captured `WeightVarianceAuthorityReadPort`, rejecting inherited Protocol placeholders and descriptors;
- binds the released #405 sampling receipt reference/version/digest to the final analysis-weight receipt digest and the separate #406 variance-design receipt reference/version/digest;
- mirrors the active scientific compatibility contract's decisive basis: exact analytic-case occurrence set, weight-eligibility receipt, integer correction sequence, and final point-weight artifact;
- requires a controlled variance method reference/version, a controlled evidence mode (`joint_inclusion`, `reproducible_design_algorithm`, `replicate_weights`, or explicit `approximation`), and exact-versus-approximate semantics; an approximation cannot be labelled exact;
- rejects a variance-design receipt digest that aliases the final point-weight receipt digest;
- requires a released owner-contract reference/version/digest and owner-resolved `released_at`, rejecting use before that release instant;
- reconstructs owner evidence into an exact tuple-backed `WeightVarianceAuthorityRecord` and fails closed if any requested scientific coordinate differs from the owner projection;
- returns only a minimized `WeightVarianceAuthorityView`. It never copies row-level point weights, replicate vectors, frame/cluster/stratum variables, protected characteristics, or foreign application-table values.

These application contracts do **not** complete #407 and do not make an arbitrary injected Python port durable scientific authority. The current branch has no durable scientific-authority relation or released auxiliary/benchmark/variance-evidence adapter. After the canonical owner persistence path is protected truth, #248 or its verified successor must implement schema-qualified least-privilege durable ports and prove that resolved owner evidence is itself released/versioned, append-only where corrected, and purpose-authorized. Mutable #57 source is not a runtime or source dependency of this service; its active compatibility and benchmark contracts were used only to align the application boundary's evidence coordinates.

`services/workforce-validation-api/database/migrations/0001_owner_schema.sql` starts this bounded context's own migration history. It creates the `workforce_validation` schema and deny-default `workforce_validation_role`, revokes public schema access, and intentionally creates or moves no application table yet. The role is a **NOLOGIN migration/schema owner only**; runtime principals must not be granted that owner role. PostgreSQL applies role-level configuration defaults at login and does not re-apply them on `SET ROLE`, so an `ALTER ROLE ... SET search_path` entry on this NOLOGIN role is not treated as a runtime isolation control. The later durable adapter must use a distinct least-privilege runtime role, schema-qualified `workforce_validation` relations, and explicit function-level `search_path` where `SECURITY DEFINER` code is introduced.

Protected foundation migrations still create validity-study tables in the legacy foundation schema, so the next forward-only persistence increment must adopt those records without normalizing `public.validity_study` as a long-lived service contract or breaking existing linkage evidence.

Issue #234 owns the remaining order: durable owner-schema adoption and PostgreSQL adapter, idempotent registration, explicit predictor/sample/decision-policy/analysis-protocol versions, scientific adapters, OpenAPI/gateway exposure, and realistic p95 measurement. Issues #236–#244 retain the current bootstrap trust-boundary findings through exact-head acceptance and protected integration: persisted-record immutability, principal immutability and constructor revalidation, owner-role/runtime-role separation, inert repository-capability validation, immutable minimized output, non-public issuance of that output, detached UUID storage/target snapshots, and exact validation of UUID internal payloads before comparison. Issue #407 additionally keeps durable scientific-authority resolution open until owner persistence/released evidence, exact-head GREEN, independent review, and protected integration are real.

## Test

The Draft branch is admitted to the canonical Foundation quality workflow with the same hash-locked test toolchain and direct source-tree dependency policy used by the existing owner services:

```bash
PYTHONPATH=services/workforce-validation-api/src:packages/keyverse-adapter/src \
  COVERAGE_FILE=/tmp/orgmetra-workforce-validation-api.coverage \
  python -m pytest -c services/workforce-validation-api/pyproject.toml \
  services/workforce-validation-api/tests
```

The service package keeps an exact 100% owned statement/branch threshold. Calibration-authority coverage exercises authorization-before-owner-read, non-concrete/dynamic owner capabilities, malformed references/digests/versions/timestamps, projection-version mismatch, foreign/mismatched owner evidence, caller/owner scientific-use-time mismatch, authorization-window mismatch, UUID alias mutation, structural immutability, and non-public view issuance. Calibration-benchmark coverage additionally exercises exact receipt/owner-contract coordinate mismatch, owner-resolved release-time enforcement, owner-contract-before-receipt chronology, future-reference rejection, append-only supersession completeness and monotonicity, successor release ordering, historical pre-supersession use, rejection at/after supersession, malformed references/digests/versions/timestamps, foreign tenant/study evidence, detached UUID views, structural immutability, and non-public output issuance. Weight/variance-authority coverage exercises every owner-coordinate mismatch, point/variance evidence aliasing, unsupported evidence modes and semantics, approximation-labelled-as-exact, pre-release use, foreign tenant/study evidence, integer correction-sequence mismatches, detached UUID views, and non-public output issuance.

The same Foundation job also runs `tests/test_workforce_validation_owner_schema_postgres.sh` in its own pinned PostgreSQL 16.14 container. That contract executes the service-local owner migration and checks the exact deny-default role flags, schema owner, absence of ineffective login-only `rolconfig`, actual `SET ROLE` search-path behavior, absence of inherited PUBLIC `USAGE`/`CREATE`, and absence of application relations in the bootstrap schema. The test intentionally demonstrates that `SET ROLE` retains the caller's existing `search_path`; runtime isolation therefore cannot be inferred from owner-role metadata.

Those source contracts are not terminal acceptance by themselves. The slice remains Draft until the exact current head actually executes with 100% owned statement/branch coverage, the PostgreSQL owner-schema contract is GREEN, applicable security workflows are terminal, and the normal review/governance requirements are satisfied. Only then may the next forward-only owner-table adoption and durable adapter be treated as eligible for integration.