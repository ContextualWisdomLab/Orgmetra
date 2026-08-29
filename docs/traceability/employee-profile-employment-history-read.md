# Employee profile Employment-history read traceability

## Product requirement

Protected Orgmetra planning requires an authoritative bitemporal HRIS core and buyer-readable employee history. Protected `develop` already stores `employment_record` and `employment_record_version` truth and exposes governed People reads, but before PR #149 it has no purpose-bound service contract for returning Employment history at an explicit system knowledge cutoff.

## Protected-main truth consumed

- `database/migrations/0001_foundation_schema.sql` separates `employment_record` identity from bitemporal `employment_record_version` business/system truth.
- `services/people-api/src/orgmetra_people_api/authorization.py` delegates protected-field authorization to the integrated purpose-bound Keyverse adapter contract.
- `services/people-api/src/orgmetra_people_api/people.py` establishes authorization-before-protected-read and target-scope revalidation.
- `services/people-api/src/orgmetra_people_api/mutations.py` defines current controlled Employment statuses (`active`, `leave`, `terminated`) and concurrency codes (`exclusive`, `concurrent`).
- `.github/workflows/people-api-quality.yml` requires exact 100% owned People API statement and branch coverage.

## PR #149 active implementation

| Requirement | Production boundary | Regression evidence |
| --- | --- | --- |
| Authorize before protected retrieval | `read_employment_history()` calls `authorize_resource_fields()` before `EmploymentHistoryReadPort` | denied-field test requires zero port calls |
| Preserve business/system time separately | `EmploymentHistoryRecord.effective_*` and `.recorded_*` | deterministic history and recorded-cutoff tests |
| Tenant/Person isolation | service revalidates every service-owned snapshot | other-tenant and other-Person rows fail closed |
| Half-open system visibility | `[recorded_from, recorded_to)` at exact `known_at` | future-recorded and `recorded_to == known_at` rows fail closed |
| Controlled Employment semantics | exact built-in status/concurrency codes | unknown and string-subclass codes fail closed |
| Field minimization | output built only from `decision.authorized_fields` | status-only grant leaks no Employment identity |
| No reflective schema expansion | explicit supported-field encoder requires exact built-in `str` | unknown and string-subclass fields fail closed |
| Persistence runtime integrity | exact tuple + exact row type + validated service-owned captures | mutable container, unsupported row, post-construction rewrite, retained-alias rewrite, and torn-capture regressions |
| Validation-to-use alias integrity | `_snapshot_persistence_record()` requires two consecutive validated service-owned captures to agree and never serializes the adapter-owned row | post-capture retained-alias mutation cannot change output; a deterministic rewrite between status/concurrency field reads must fail closed rather than authorize a mixed row |
| Version integrity | unique `employment_record_version_id` per response snapshot | duplicate version identity fails closed |
| Bitemporal business integrity | visible snapshots of one Employment cannot overlap effective time | overlapping intervals fail closed; adjacent intervals remain valid |
| Deterministic history | sort by effective start, Employment UUID, version UUID | reversed persistence order returns canonical order |
| Trust-bearing identity/time integrity | exact operational UUIDs and built-in UTC instants | sentinel/subclass UUID and malformed system time fail before protected retrieval or row use |

## Scope exclusions

PR #149 does not create/update/delete Employment, alter schema, expose a PostgreSQL adapter, add UI geometry, infer attendance/fitness/compensation/performance, or authorize an employment decision. It does not mutate Keyverse or any other dedicated-writer repository. A future persistence adapter and employee-profile UI must reuse this contract instead of bypassing the People service.

The stable-capture check detects in-process source changes observed across two consecutive validated captures. It does not claim to replace database transaction isolation, MVCC, locks, or a persistence adapter's obligation to return one coherent view.

## Test-first evidence rule

Contract head `23c3417edd7024ecc4c1c64f2d7017b573ab9eaf` added the original executable regression before production `employment_history.py` existed. Hosted execution for that predecessor was queued when the implementation branch advanced, so queued/cancelled predecessor evidence is **not** represented as a terminal RED. The contract-first source ordering remains auditable in Git history.

A later integrity review identified a second, narrower validation-to-use defect: the service revalidated the exact persistence-owned `EmploymentHistoryRecord` and then retained that same object for overlap checks and authorized encoding. Because `object.__setattr__` can rewrite a frozen dataclass through an alias, a holder of the persistence row could change an already-validated value before use. Exact head `5cdbeb2028a49bd0277159a03042c5d95dd2a06d` added the realistic alias-rewrite regression before the root repair; the production repair begins at `45b4ff5ec9fb065a665e1fe51bc2120d46cdc62a` by reconstructing a service-owned validated snapshot and discarding the persistence alias for subsequent decisions and output.

A third integrity review identified a capture-window defect in that repair: one sequential reconstruction could read an old value for one field and a concurrently rewritten value for a later field, producing a valid-looking service-owned row that never existed as one source state. Exact head `6eb105d6310adbdb9e33f64fab4cd450a9681968` added `test_alias_rewrite_during_snapshot_cannot_create_torn_authorized_row` before the production change. Its workflows were still queued when the branch advanced, so no terminal RED is claimed. The root repair begins at `4dfbd2a9f32947e5c1c61d6eccee47b57781dc92`: two consecutive validated captures must compare equal before the second detached capture is trusted.

Only tests/checks bound to the final unchanged PR #149 head are passing integration evidence. Queued, pending, skipped, cancelled, absent, predecessor-head, status-only, or model-only evidence is non-passing, and another PR's checks/reviews never transfer.
