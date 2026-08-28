# Employee profile assignment-history read traceability

## Product requirement

Protected `docs/PRD.md` lists **Employee profile with bitemporal assignment history** as a P1 HRIS requirement. PR #142 owns only the backend governed-read slice needed to expose Assignment history to an employee-profile surface.

## Protected-main truth consumed

- `packages/hris-kernel/src/orgmetra_hris_kernel/facts.py` defines immutable `AssignmentFact` identity, Employment/Person/Position binding, exact allocation, business-effective interval, and system-recorded interval.
- `services/people-api/src/orgmetra_people_api/authorization.py` delegates field access to the existing purpose-bound Keyverse adapter contract.
- `services/people-api/src/orgmetra_people_api/people.py` establishes the People API pattern that authorizes before protected repository access and revalidates resolved target scope.
- `.github/workflows/people-api-quality.yml` requires exact 100% People API statement and branch coverage.

## PR #142 active implementation

| Requirement | Production boundary | Regression evidence |
| --- | --- | --- |
| Authorize before protected retrieval | `read_assignment_history()` calls `authorize_resource_fields()` before `AssignmentHistoryReadPort` | denied-field test asserts zero port calls |
| Preserve business and system time separately | `AssignmentHistoryRecord.effective_*` and `.recorded_*` | visible/history ordering and recorded-cutoff regressions |
| Deterministic UTC trust boundary | `known_at` and recorded instants require an exact `datetime` using Python's built-in fixed-offset `timezone` at zero offset | caller-defined UTC-looking `tzinfo` providers fail before protected retrieval and at persistence-row construction |
| Tenant/person isolation | service revalidates every returned row | other-tenant and other-person rows fail closed |
| Half-open system-time visibility | `[recorded_from, recorded_to)` at exact `known_at` | future-recorded and `recorded_to == known_at` rows fail closed |
| Field minimization | output is built only from `decision.authorized_fields` | effective-only policy does not leak assignment identity |
| No reflective schema expansion | explicit supported-field encoder requires an exact built-in `str` | unknown fields and string-subclass fields fail closed |
| Deterministic history | sort by effective start then assignment UUID | reversed persistence order produces deterministic business-time order |
| Exact allocation evidence | finite four-decimal `Decimal` in `(0, 1.0000]` | NaN, zero, >1, and noncanonical scale rejected |
| Trust-bearing identity integrity | operational identity requires exact built-in `UUID`, not subclasses or sentinel values | UUID subclasses plus Nil/Max sentinels are rejected |
| Persistence runtime integrity | exact tuple + exact row type + `AssignmentHistoryRecord.assert_runtime_integrity()` immediately after retrieval | mutable container, unsupported row type, and post-construction NaN reinjection fail closed |

## Scope exclusions

PR #142 does **not** create or change Assignment, Employment, Position, Person, candidate, compensation, performance, or decision records. It adds no UI geometry and does not write to Keyverse or another CWL repository. A PostgreSQL persistence adapter and employee-profile UI wiring remain separate follow-on work and must reuse this contract rather than bypass it.

## Merge evidence rule

Only evidence bound to the final unchanged PR #142 head is applicable. Pending, queued, skipped, cancelled, predecessor-head, status-only, or model-only evidence is non-passing. Reviews/checks from another PR do not transfer.
