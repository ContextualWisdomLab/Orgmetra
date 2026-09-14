# Employee profile Employment-history read traceability

## Product requirement

Protected Orgmetra planning requires an authoritative bitemporal HRIS core and buyer-readable employee history. Protected `develop` already stores `employment_record` and `employment_record_version` truth and exposes governed People reads, but before PR #149 it has no purpose-bound service contract for returning Employment history at an explicit system knowledge cutoff.

## Canonical owner relationship

PR #55 is the single writer for governed People-read infrastructure. PR #149 is a dependent Employment-history read extension, not a competing People-read owner. After first adopting protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`, #149 adopted exact #55 head `147b8fc2f1938cb69b45532a0418ae78dca0be30` by ordinary two-parent merge `22ab29277b37c593b5010b8cb02b2c6d486ffbf6` and was retargeted to `fix/people-read-auth-backend-failure`. The resulting comparison remains 0-behind; the descendant delta is confined to Employment-history production, tests, ADR/doctoring/traceability, and package exports. #55 must integrate normally first; #149 then non-force adopts protected owner truth and reacquires final-head evidence.

## Protected truth consumed

- `database/migrations/0001_foundation_schema.sql` separates `employment_record` identity from bitemporal `employment_record_version` business/system truth.
- `services/people-api/src/orgmetra_people_api/authorization.py` delegates protected-field authorization to the integrated purpose-bound Keyverse adapter contract.
- `services/people-api/src/orgmetra_people_api/people.py` establishes authorization-before-protected-read, static pre-authorization repository-capability binding, and target-scope revalidation; #55 owns its governed-read hardening.
- `services/people-api/src/orgmetra_people_api/mutations.py` defines current controlled Employment statuses (`active`, `leave`, `terminated`) and concurrency codes (`exclusive`, `concurrent`).
- `.github/workflows/foundation-ci.yml` is the current repository-owned exact-head quality owner after protected PR #161 consolidated the former leaf People API workflow.

## PR #149 active implementation

| Requirement | Production boundary | Regression evidence |
| --- | --- | --- |
| Bind exact persistence capability before authorization | `read_employment_history()` resolves the concrete `read_employment_history` function with `getattr_static()` before policy evaluation and invokes that retained function directly afterward | dynamic instance lookup trap and authorization-time class substitution both fail unless the pre-authorization function is retained |
| Authorize before protected retrieval | `read_employment_history()` calls `authorize_resource_fields()` before invoking the retained `EmploymentHistoryReadPort` capability | denied-field test requires zero port calls |
| Preserve business/system time separately | `EmploymentHistoryRecord.effective_*` and `.recorded_*` | deterministic history and recorded-cutoff tests |
| Tenant/Person isolation | request UUIDs are detached to immutable scalars; every persistence row is reconstructed and compared to those scalars | other-tenant and other-Person rows fail closed |
| Half-open system visibility | `[recorded_from, recorded_to)` at exact `known_at` | future-recorded and `recorded_to == known_at` rows fail closed |
| Controlled Employment semantics | exact built-in status/concurrency codes | unknown and string-subclass codes fail closed |
| Field minimization | output built only from `decision.authorized_fields` | status-only grant leaks no Employment identity |
| No reflective schema expansion | authorization output is validated as exact built-in supported field names before persistence; explicit encoder remains the emission boundary | unknown/string-subclass fields fail closed, including an empty-history schema-drift regression with zero port calls |
| Exact persistence row shape | exact `EmploymentHistoryRecord` rows must also contain exactly the declared namedtuple field count before descriptor-backed access | low-level tuples with missing or extra fields fail as `EmploymentHistoryIntegrityError` rather than leaking `IndexError` or ignoring payload |
| Persistence runtime integrity | raw scalar validation precedes UUID reconstruction; exact tuple/row type and row shape are then reconstructed through the public validator | mutable container, unsupported row, forged status, and forged non-int scalar regressions |
| Top-level row alias integrity | tuple-backed row state prevents `object.__setattr__` from replacing fields | retained-row status rewrite attempts fail at the row boundary |
| Nested UUID alias integrity | trust-bearing UUIDs are validated once, stored as exact built-in integer scalars, and exposed only as fresh UUID views | constructor-owned aliases, exposed UUID views, behavior-bearing payloads, and forged out-of-range payloads are regression-tested |
| Version integrity | unique `employment_record_version_id_scalar` per response snapshot | duplicate version identity fails closed |
| Bitemporal business integrity | visible snapshots of one Employment cannot overlap effective time | overlapping intervals fail closed; adjacent intervals remain valid |
| Deterministic history | sort by effective start, immutable Employment scalar, immutable version scalar | reversed persistence order returns canonical order |
| Trust-bearing identity/time integrity | exact operational UUID inputs detach to immutable scalar authority; system instants require built-in UTC values | sentinel/subclass/forged UUID payloads and malformed system time fail before protected retrieval or row use |

## Scope exclusions

PR #149 does not create/update/delete Employment, alter schema, expose a PostgreSQL adapter, add UI geometry, infer attendance/fitness/compensation/performance, or authorize an employment decision. It does not mutate Keyverse or another dedicated-writer repository. A future persistence adapter and employee-profile UI must reuse this contract instead of bypassing the People service.

The in-process row object uses tuple-backed state and immutable scalar identity storage, and the service revalidates exact row shape, raw scalar state, plus a detached reconstruction before authorization output. The authorization field schema is validated independently of result cardinality before protected retrieval. Static capability binding prevents a post-decision executable lookup from changing which repository function runs. These controls do not claim to replace database transaction isolation, MVCC, locks, or a persistence adapter's obligation to return one coherent view.

## Test-first evidence rule

Contract head `23c3417edd7024ecc4c1c64f2d7017b573ab9eaf` added the original executable regression before production `employment_history.py` existed. Hosted execution for that predecessor was queued when the implementation branch advanced, so queued/cancelled predecessor evidence is **not** represented as a terminal RED.

A later integrity review found a validation-to-use alias defect. Exact head `5cdbeb2028a49bd0277159a03042c5d95dd2a06d` added the retained-alias regression before repair `45b4ff5ec9fb065a665e1fe51bc2120d46cdc62a` reconstructed service-owned snapshots.

A subsequent capture-window review found that sequential reconstruction could observe a torn source state. Exact head `6eb105d6310adbdb9e33f64fab4cd450a9681968` added that regression before repair `4dfbd2a9f32947e5c1c61d6eccee47b57781dc92`. Its workflows had not reached a terminal RED before the branch advanced.

The next review found that a frozen dataclass itself remained rewritable through `object.__setattr__`. Exact test-only head `c07ce7baf738679e1ef5cbef1d98760fefe670e3` produced a genuine hosted RED in People API Quality run `33257244737` / job `99113016031`: 1 failed / 159 passed. Repair `6ef636cdf803ef3195f80db089f1ee432e0d7646` moved the row to tuple-backed storage while retaining validating reconstruction.

Protected PR #161 then consolidated repository quality workflows. PR #149 adopted current protected `develop` through ordinary two-parent merge `6185e71ed92fa222ceffb99d8c44c1ed6784eadd`, removing stale leaf-workflow assumptions without source loss.

A fifth integrity review found that tuple-backed storage still retained mutable exact `UUID` objects. Test-first head `450bf24abf2cbc51077f77a934261e807beabca7` added constructor-alias, exposed-view, behavior-bearing payload, and out-of-range payload regressions. No hosted RED is claimed for that short-lived head. A source-equivalent reproduction changed all four previously validated identities through retained UUID aliases. Repair `61d63e7d611357231e11fce2762c3f9698c97867`, simplified at `33dce8059b8d4dac9c566b80ad78dc869e10ecbe`, stores only exact built-in integer identity scalars, returns fresh UUID views, and binds scope/duplicate/sort decisions to immutable scalar authority.

A sixth review found one constructor-bypass edge left by that repair: a low-level exact tuple could place a non-integer object in a scalar slot, and `_capture_persistence_record()` reconstructed `UUID(int=raw_scalar)` before validating raw scalar state. Python raises `TypeError` for `UUID(int=object())`, outside the service's stable `ValueError`→`EmploymentHistoryIntegrityError` boundary. Test-first head `e17539f693bb8f2823e71b7b6e13a0891e4a79cc` adds the public-service regression; no hosted RED is claimed because no run materialized before the branch advanced. Repair `b8405a2143d10751ccf51615abaac5c93b2917b5` calls `record.assert_runtime_integrity()` before any UUID view reconstruction, so forged scalar state fails as a stable integrity error before conversion behavior can run. A focused source-equivalent check reproduced predecessor `TypeError` and repaired `ValueError` ordering; that local evidence is not a substitute for hosted CI.

The dependent lane then adopted canonical People-read owner #55 by ordinary merge `22ab29277b37c593b5010b8cb02b2c6d486ffbf6` and retargeted to #55's branch. No #55 source was copied into a parallel owner lane; the owner remains the PR parent.

A seventh current-head review found two independent fail-open/unstable edges. Low-level `tuple.__new__` could construct an exact `EmploymentHistoryRecord` with too few fields, leaking `IndexError`, or with extra fields that were silently ignored. Separately, policy-schema drift was discovered only while encoding a non-empty result, so an empty history could return successfully with an unsupported authorized field. Test-first commit `441fa306c7fbfae0869577caf34c60b41f848145` added public-service regressions for both cases before production repair. Because #149 is intentionally stacked on #55 and the protected Foundation pull-request workflow targets `develop`, no hosted RED is claimed for this stacked test-only head. Repair `ca9d3cf1511ea9fcdddfc4c09129b1249c2ff6d0` validates exact row cardinality before any field descriptor access and validates the authorized response schema immediately after authorization, before protected persistence. The latter makes unsupported schema fail closed even for an empty history and keeps the repository unread in that case.

An eighth review compared #149 with canonical People-read owner #55 and found a checked-vs-used capability gap: Employment history performed a fresh `read_port.read_employment_history` instance lookup only after authorization, while #55 already freezes the concrete repository function before the access decision. Test-first commits `f2e41e8afe5387be3b7a662fe2fd842b4d7ab481` and `602c5cf2c604fc6e5f677f782a424531c207452c` add regressions for a hostile dynamic instance lookup and for authorization-time replacement of the repository class method. No hosted RED is claimed because the PR remains intentionally stacked on #55 and therefore does not trigger the protected `pull_request -> develop` Foundation workflow. Repair `54fe8a78239d7b0c7fcb9daf09bcd085ee1d61b1` now uses `getattr_static()` to retain one exact concrete function before authorization, rejects the Protocol placeholder/non-function descriptor, and invokes that retained function directly afterward. This preserves #55's canonical capability-integrity invariant without copying its domain implementation.

ADR 0149 remains **Proposed** while PR #149 is active. It must not become Accepted until the repaired feature reaches normal protected integration after its owner prerequisite.

Only tests/checks bound to the final unchanged PR #149 head are passing integration evidence. Queued, pending, skipped, cancelled, absent, predecessor-head, status-only, local-reproduction, or model-only evidence is non-passing, and another PR's checks/reviews never transfer.
