# Employee profile Employment-history read traceability

## Product requirement

Protected Orgmetra planning requires an authoritative bitemporal HRIS core and buyer-readable employee history. Protected `develop` already stores `employment_record` and `employment_record_version` truth and exposes governed People reads, but before PR #149 it has no purpose-bound service contract for returning Employment history at an explicit system knowledge cutoff.

## Protected develop truth consumed

- `database/migrations/0001_foundation_schema.sql` separates `employment_record` identity from bitemporal `employment_record_version` business/system truth.
- `services/people-api/src/orgmetra_people_api/authorization.py` delegates protected-field authorization to the integrated purpose-bound Keyverse adapter contract.
- `services/people-api/src/orgmetra_people_api/people.py` establishes authorization-before-protected-read and target-scope revalidation.
- `services/people-api/src/orgmetra_people_api/mutations.py` defines current controlled Employment statuses (`active`, `leave`, `terminated`) and concurrency codes (`exclusive`, `concurrent`).
- `.github/workflows/foundation-ci.yml` is the current repository-owned exact-head quality owner after protected PR #161 consolidated the former leaf People API workflow. Its unit/service phase runs the People API suite under the reviewed toolchain; PR #149 must satisfy that current Foundation gate rather than rely on the removed `.github/workflows/people-api-quality.yml`.

## PR #149 active implementation

| Requirement | Production boundary | Regression evidence |
| --- | --- | --- |
| Authorize before protected retrieval | `read_employment_history()` calls `authorize_resource_fields()` before `EmploymentHistoryReadPort` | denied-field test requires zero port calls |
| Preserve business/system time separately | `EmploymentHistoryRecord.effective_*` and `.recorded_*` | deterministic history and recorded-cutoff tests |
| Tenant/Person isolation | request UUIDs are detached to immutable scalars; every persistence row is reconstructed and compared to those scalars | other-tenant and other-Person rows fail closed |
| Half-open system visibility | `[recorded_from, recorded_to)` at exact `known_at` | future-recorded and `recorded_to == known_at` rows fail closed |
| Controlled Employment semantics | exact built-in status/concurrency codes | unknown and string-subclass codes fail closed |
| Field minimization | output built only from `decision.authorized_fields` | status-only grant leaks no Employment identity |
| No reflective schema expansion | explicit supported-field encoder requires exact built-in `str` | unknown and string-subclass fields fail closed |
| Persistence runtime integrity | exact tuple + exact row type + validating service-owned reconstruction | mutable container, unsupported row, and low-level forged exact-type regressions |
| Top-level row alias integrity | tuple-backed row state prevents `object.__setattr__` from replacing fields | retained-row status rewrite attempts fail at the row boundary |
| Nested UUID alias integrity | trust-bearing UUIDs are validated once, stored as exact built-in integer scalars, and exposed only as fresh UUID views | constructor-owned aliases, exposed UUID views, behavior-bearing payloads, and forged out-of-range payloads are regression-tested |
| Version integrity | unique `employment_record_version_id_scalar` per response snapshot | duplicate version identity fails closed |
| Bitemporal business integrity | visible snapshots of one Employment cannot overlap effective time | overlapping intervals fail closed; adjacent intervals remain valid |
| Deterministic history | sort by effective start, immutable Employment scalar, immutable version scalar | reversed persistence order returns canonical order |
| Trust-bearing identity/time integrity | exact operational UUID inputs detach to immutable scalar authority; system instants require built-in UTC values | sentinel/subclass/forged UUID payloads and malformed system time fail before protected retrieval or row use |

## Scope exclusions

PR #149 does not create/update/delete Employment, alter schema, expose a PostgreSQL adapter, add UI geometry, infer attendance/fitness/compensation/performance, or authorize an employment decision. It does not mutate Keyverse or any other dedicated-writer repository. A future persistence adapter and employee-profile UI must reuse this contract instead of bypassing the People service.

The in-process row object uses tuple-backed state and immutable scalar identity storage, and the service revalidates a detached reconstruction before authorization output. This does not claim to replace database transaction isolation, MVCC, locks, or a persistence adapter's obligation to return one coherent view.

## Test-first evidence rule

Contract head `23c3417edd7024ecc4c1c64f2d7017b573ab9eaf` added the original executable regression before production `employment_history.py` existed. Hosted execution for that predecessor was queued when the implementation branch advanced, so queued/cancelled predecessor evidence is **not** represented as a terminal RED. The contract-first source ordering remains auditable in Git history.

A later integrity review identified a second, narrower validation-to-use defect: the service revalidated the exact persistence-owned `EmploymentHistoryRecord` and then retained that same object for overlap checks and authorized encoding. Because `object.__setattr__` can rewrite a frozen dataclass through an alias, a holder of the persistence row could change an already-validated value before use. Exact head `5cdbeb2028a49bd0277159a03042c5d95dd2a06d` added the realistic alias-rewrite regression before the root repair; the production repair begins at `45b4ff5ec9fb065a665e1fe51bc2120d46cdc62a` by reconstructing a service-owned validated snapshot and discarding the persistence alias for subsequent decisions and output.

A third integrity review identified a capture-window defect in that repair: one sequential reconstruction could read an old value for one field and a concurrently rewritten value for a later field, producing a valid-looking service-owned row that never existed as one source state. Exact head `6eb105d6310adbdb9e33f64fab4cd450a9681968` added `test_alias_rewrite_during_snapshot_cannot_create_torn_authorized_row` before the production change. Its workflows were still queued when the branch advanced, so no terminal RED is claimed. The prior repair beginning at `4dfbd2a9f32947e5c1c61d6eccee47b57781dc92` required two consecutive validated captures to compare equal.

A fourth integrity review identified the remaining top-level weakness: the double-capture guard still accepted a record type whose row fields could be rewritten through `object.__setattr__`. Exact test-only head `c07ce7baf738679e1ef5cbef1d98760fefe670e3` added `test_persistence_record_is_structurally_immutable_against_object_setattr`. People API Quality run `33257244737`, exact checkout job `99113016031`, produced a genuine terminal RED: 1 failed / 159 passed, with the new test failing because `object.__setattr__` did **not** raise; owned production coverage remained 1524/1524 statements and 508/508 branches. The repair beginning at `6ef636cdf803ef3195f80db089f1ee432e0d7646` moved row fields to tuple-backed storage while retaining validating reconstruction for low-level exact-type instances.

Protected PR #161 later consolidated repository quality workflows. PR #149 adopted current protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` by ordinary two-parent merge `6185e71ed92fa222ceffb99d8c44c1ed6784eadd`; the seven-file Employment-history feature delta did not overlap the protected consolidation delta. This deliberately removed the stale branch-owned People API workflow from the candidate before further repair.

A fifth integrity review then identified a nested alias defect that tuple-backed row storage alone did not solve: Python's exact `UUID` object can have its internal `int` rewritten through `object.__setattr__`, so the tuple still retained mutable identity objects supplied by the caller. Test-first head `450bf24abf2cbc51077f77a934261e807beabca7` adds regressions for constructor-retained UUID aliases, response-exposed UUID aliases, behavior-bearing forged UUID payloads, and out-of-range exact UUID payloads. No hosted RED is claimed for that predecessor because no PR workflow run materialized before the branch advanced. A local source-equivalent reproduction of the exact predecessor identity-storage logic changed all four already-validated record identities after mutating the retained UUID aliases, establishing the concrete failure mechanism without upgrading that reproduction to hosted evidence.

The causal repair begins at `61d63e7d611357231e11fce2762c3f9698c97867` and is simplified at `33dce8059b8d4dac9c566b80ad78dc869e10ecbe`: every incoming exact UUID is reduced to an exact built-in integer inside the operational range before it can become stored authority; the row stores those immutable scalars, public identity properties return fresh UUID views, request tenant/Person identities are detached before authorization and the untrusted persistence call, and duplicate/scope/sort logic uses scalar authority instead of mutable UUID objects.

ADR 0149 remains **Proposed** while PR #149 is active. It must not become Accepted until the repaired exact head reaches normal protected integration.

Only tests/checks bound to the final unchanged PR #149 head are passing integration evidence. Queued, pending, skipped, cancelled, absent, predecessor-head, status-only, local-reproduction, or model-only evidence is non-passing, and another PR's checks/reviews never transfer.
