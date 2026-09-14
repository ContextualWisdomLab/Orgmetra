# Position history read traceability

**Lifecycle status:** Proposed in active PR #152. This document describes the PR contract, not protected `develop` truth until integration.

## Buyer outcome

An authorized HR operator can inspect the bitemporal history of one Position for a declared workforce purpose without receiving unrelated Person, Employment, Assignment, candidate, compensation, or decision data.

## Protected-main prerequisites

Protected `develop` provides the authoritative data-model separation and repository-wide quality workflow used by this slice:

| Concern | Protected truth used by #152 |
| --- | --- |
| Job | `job_profile` remains reusable Job/work content. |
| Position | `position_record` remains a tenant-owned Position anchor with organization and Job lineage. |
| Position version | `position_record_version` preserves business-effective and system-recorded time. |
| Assignment | `assignment_record` remains distinct from Position and links the worker/employment relationship to a Position. |
| Authorization | People service uses purpose-bound policy evaluation before protected reads. |
| Repository acceptance | consolidated `.github/workflows/foundation-ci.yml` owns repository unit/service/PostgreSQL validation; feature-local duplicate quality workflows are not canonical owners. |

#152 does not add a database migration, mutate those tables, or create cross-service application-table SQL.

## Requirement-to-evidence matrix

| Requirement | Implementation boundary | Executable evidence |
| --- | --- | --- |
| Authorize before retrieval | `read_position_history()` captures the repository function and immutable request identity before the purpose-bound authorization boundary | denied fields and dynamic-lookup traps prove retrieval cannot move ahead of or substitute around authorization |
| Stable tenant/Position authority | request UUIDs are reduced to exact built-in integer scalars before authorization/persistence; fresh UUID views are reconstructed only at typed boundaries | a repository that mutates the UUID object it receives cannot change the authorized target |
| Stable row identity | `PositionHistoryRecord` stores tenant/Position/version/organization/Job UUID authority as built-in integer scalars and exposes detached UUID views | mutating every constructor UUID alias after construction leaves record identity unchanged |
| Tenant/context isolation | detached row scalars are rechecked against the authorized tenant/Position scalars | wrong-tenant and wrong-Position rows fail closed |
| Bitemporal system truth | half-open `recorded_from`/`recorded_to` at exact UTC `known_at` | future and already-closed rows fail closed |
| Business-time consistency | visible half-open effective intervals may not overlap; absent ends remain semantically unbounded rather than mapped to `date.max` | ordinary-overlap and `date.max` open-interval regressions fail closed |
| Immutable evidence | exact tuple container and exact `PositionHistoryRecord`; raw scalar-backed state is revalidated before detached reconstruction | unsupported container/type, forged values, and short low-level row all fail closed |
| Opaque identifiers | exact operational UUIDs are detached to exact built-in scalar authority; nil/max protocol sentinels, subclasses, and forged scalar payloads are rejected | invalid request/record and retained-alias regressions |
| Field minimization | authorized field schema is validated before protected retrieval and serialized through an explicit whitelist | one-field policy returns one field; unsupported/subclass fields fail closed even when persistence would return no rows |
| Checked-versus-used repository capability | concrete class function captured with inert lookup before authorization and called directly afterward | instance lookup trap cannot replace or intercept the protected read capability |
| Deterministic history | sort by effective start then immutable version scalar | reversed persistence order produces deterministic output |
| Job/Position/Assignment separation | view contains Position/Job lineage only; no worker/Assignment expansion | schema and response contract |
| Exact owned coverage | consolidated Foundation CI People service contract | 100% statement and branch gate on exact current head required |

## Test-first chain

1. **Initial test-only head:** `d751f117e37e2169015004ab89fa728731b2a7ec`.
2. **Initial hosted RED:** People API Quality run `33267334677`, job `99139623454`, failed during collection because `orgmetra_people_api.position_history` did not exist.
3. **Root implementation:** `f633aa3d008d7832759bb83dead8d4e5a6977a8b` added the smallest Orgmetra-owned read boundary.
4. **Coverage gate held:** run `33267487363`, job `99140037925`, passed all 156 tests but correctly failed exact coverage because one deliberate malformed-row branch remained unexecuted.
5. **Regression strengthening:** `cbb343a40864694ac243946615aee5f91685beda` added a low-level short-row reconstruction regression.
6. **Exact GREEN at that predecessor:** People API Quality run `33267577477`, job `99140279359`: 157 tests; 1,543/1,543 statements; 504/504 branches; compile and clean-checkout GREEN.
7. **Extreme-date integrity RED:** source review found that `_business_intervals_overlap()` substituted finite `date.max` for an absent business end. Test-only head `af8d0b9b88c50f17c87eb8ecf1eea29918835dce` added a valid `[date.max, ∞)` overlap case. People API Quality run `33267978859`, job `99141335635`, checked out that exact SHA and failed exactly that regression: **1 failed / 157 passed** while owned production coverage remained **1,544/1,544 statements and 504/504 branches = 100.00%**.
8. **Extreme-date root repair:** `955956f838c467c06c25b63127b7c6e976dea812` removes the finite-infinity sentinel and compares optional interval endpoints directly.
9. **Protected-workflow reconciliation:** ordinary two-parent commit `f79adf291bdd030791bc196d09ba732fa54fa755` adopts protected `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` while preserving the eight #152 feature files. No force push or destructive rebase is used.
10. **Retained-authority test-only head:** `bcab0d4949ea9318e97d4a5de0d373a8cf7773ee` adds four regressions: constructor UUID alias mutation, post-authorization request identity mutation, unsupported field schema with an empty repository result, and dynamic repository instance lookup. Foundation CI `34811863983`, Security `34811863936`, CodeQL `34811864040`, and SAST `34811863933` materialized for that exact test-only head but were still queued when the causal production repair proceeded; no hosted RED is claimed for those runs.
11. **Retained-authority production repair:** `0295d06c79ca9d4bdf8bb4f6ab49be28504fa29b` stores Position-history UUID authority as built-in integer scalars, snapshots request identity before authorization, validates disclosure schema before persistence, captures the concrete repository function before authorization, and reconstructs detached trusted rows before scope/time/overlap/disclosure checks.
12. **ADR lifecycle correction:** `37c16f44a612faa1a6699259861e9f70391d959f` lowers ADR 0152 from premature Accepted-for-PR wording to `Proposed` and records the new trust boundaries.

Every material follow-up invalidates predecessor GREEN as merge evidence. The final exact PR head must receive fresh hosted acceptance and qualifying independent review before protected integration.

## Security/privacy invariants

- No PII is added to the Position-history response merely because it exists elsewhere in HRIS.
- No dynamic attribute access is used to serialize policy-controlled field names.
- Exact UUID wrappers are not retained as trust authority across authorization or persistence boundaries; built-in integer scalars are the in-process identity authority.
- The repository executable capability used after authorization is the exact class function captured before authorization; a second instance lookup is forbidden.
- Authorized response schema is validated before protected persistence, independent of result cardinality.
- Caller-controlled UUID/string/timezone subclasses do not participate in identity, authorization, chronology, or output canonicalization.
- Persistence output is revalidated and detached before scope or disclosure decisions.
- Open-ended business-time semantics are represented explicitly; runtime maximum dates are never overloaded as infinity.
- Application checks do not claim to replace database snapshot/MVCC semantics for concurrent writes.

## Out of scope / planned separately

- Position-history HTTP presentation (#154).
- Position mutation/correction workflow.
- Assignment or Employment history joins.
- Compensation, candidate, performance, or selection-decision expansion.
- Database-specific Position-history adapter and its transaction-isolation proof (#153).
- Release/version/tag publication.

Any later slice must keep these concerns bounded and must not infer protected availability from this active-PR traceability document.
