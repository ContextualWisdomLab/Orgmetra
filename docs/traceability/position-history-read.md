# Position history read traceability

**Lifecycle status:** Active PR #152. This document describes the PR contract, not protected-main truth until integration.

## Buyer outcome

An authorized HR operator can inspect the bitemporal history of one Position for a declared workforce purpose without receiving unrelated Person, Employment, Assignment, candidate, compensation, or decision data.

## Protected-main prerequisites

Protected `develop` already provides the authoritative data-model separation needed by this slice:

| Concern | Protected-main truth used by #152 |
| --- | --- |
| Job | `job_profile` remains reusable Job/work content. |
| Position | `position_record` remains a tenant-owned Position anchor with organization and Job lineage. |
| Position version | `position_record_version` preserves business-effective and system-recorded time. |
| Assignment | `assignment_record` remains distinct from Position and links the worker/employment relationship to a Position. |
| Authorization | People service uses purpose-bound policy evaluation before protected reads. |

#152 does not add a database migration, mutate those tables, or create cross-service application-table SQL.

## Requirement-to-evidence matrix

| Requirement | Implementation boundary | Executable evidence |
| --- | --- | --- |
| Authorize before retrieval | `read_position_history()` calls the purpose-bound authorization boundary before `PositionHistoryReadPort` | denied fields prove the port is never called |
| Tenant/context isolation | exact tenant and Position are rechecked on every returned row | wrong-tenant and wrong-Position rows fail closed |
| Bitemporal system truth | half-open `recorded_from`/`recorded_to` at exact UTC `known_at` | future and already-closed rows fail closed |
| Business-time consistency | visible half-open effective intervals may not overlap; absent ends remain semantically unbounded rather than mapped to `date.max` | ordinary-overlap and `date.max` open-interval regressions fail closed |
| Immutable evidence | exact tuple container and exact `PositionHistoryRecord`; runtime revalidation after low-level reconstruction | unsupported container/type, forged values, and short low-level row all fail closed |
| Opaque identifiers | exact operational UUIDs; nil/max protocol sentinels and subclasses rejected | invalid request/record regressions |
| Field minimization | explicit serializer whitelist over authorized fields only | one-field policy returns one field; unknown/subclass fields fail closed |
| Deterministic history | sort by effective start then version identity | reversed persistence order produces deterministic output |
| Job/Position/Assignment separation | view contains Position/Job lineage only; no worker/Assignment expansion | schema and response contract |
| Exact owned coverage | People API quality workflow | 100% statement and branch gate on exact current head required |

## Test-first chain

1. **Initial test-only head:** `d751f117e37e2169015004ab89fa728731b2a7ec`.
2. **Initial hosted RED:** People API Quality run `33267334677`, job `99139623454`, failed during collection because `orgmetra_people_api.position_history` did not exist.
3. **Root implementation:** `f633aa3d008d7832759bb83dead8d4e5a6977a8b` added the smallest Orgmetra-owned read boundary.
4. **Coverage gate held:** run `33267487363`, job `99140037925`, passed all 156 tests but correctly failed exact coverage because one deliberate malformed-row branch remained unexecuted.
5. **Regression strengthening:** `cbb343a40864694ac243946615aee5f91685beda` added a low-level short-row reconstruction regression.
6. **Exact GREEN at that predecessor:** People API Quality run `33267577477`, job `99140279359`: 157 tests; 1,543/1,543 statements; 504/504 branches; compile and clean-checkout GREEN.
7. **Extreme-date integrity RED:** source review found that `_business_intervals_overlap()` substituted finite `date.max` for an absent business end. Test-only head `af8d0b9b88c50f17c87eb8ecf1eea29918835dce` added a valid `[date.max, ∞)` overlap case. People API Quality run `33267978859`, job `99141335635`, checked out that exact SHA and failed exactly that regression: **1 failed / 157 passed** while owned production coverage remained **1,544/1,544 statements and 504/504 branches = 100.00%**. The service returned instead of raising `PositionHistoryIntegrityError`, proving a real business-time integrity defect rather than a coverage artifact.
8. **Extreme-date root repair:** `955956f838c467c06c25b63127b7c6e976dea812` removes the finite-infinity sentinel and compares optional interval endpoints directly. Open-ended intervals therefore remain unbounded even at the maximum representable finite date.

Documentation commits after the root repair invalidate predecessor GREEN as merge evidence. The final exact PR head must receive its own fresh hosted evidence before advancement.

## Security/privacy invariants

- No PII is added to the Position-history response merely because it exists elsewhere in HRIS.
- No dynamic attribute access is used to serialize policy-controlled field names.
- Caller-controlled UUID/string/timezone subclasses do not participate in identity, authorization, chronology, or output canonicalization.
- Persistence is an injected boundary and its output is revalidated.
- Open-ended business-time semantics are represented explicitly; runtime maximum dates are never overloaded as infinity.
- Application checks do not claim to replace database snapshot/MVCC semantics for concurrent writes.

## Out of scope / planned separately

- Position-history HTTP presentation.
- Position mutation/correction workflow.
- Assignment or Employment history joins.
- Compensation, candidate, performance, or selection-decision expansion.
- Database-specific Position-history adapter and its transaction-isolation proof.
- Release/version/tag publication.

Any later slice must keep these concerns bounded and must not infer protected-main availability from this active-PR traceability document.
