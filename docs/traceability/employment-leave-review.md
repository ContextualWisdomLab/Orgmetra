# Employment leave review traceability

Status: `implemented_on_active_pr` only. This document does not describe protected-`develop` capability until the owning PR is integrated.

| Requirement | Implemented boundary | Evidence | Maturity |
|---|---|---|---|
| Correlate one leave review to authoritative worker scope without copying worker values | `EmploymentLeaveReviewPacket` binds Person, Employment and active Assignment/Job/Position snapshot references/digest | valid-packet and canonical-payload regressions | implemented_on_active_pr |
| Bind exact leave case and policy provenance | UUID-backed `leave_case_reference` and `leave_policy_reference` with independent SHA-256 digests | namespace/digest regressions | implemented_on_active_pr |
| Prevent medical/family details from entering a portable governance artifact | no substantive leave reason, medical/family values, credentials, or free-form case/model narrative; workflow `reason_code` is restricted to non-sensitive categories | privacy-flag and rejected-sensitive-reason regressions | implemented_on_active_pr |
| Version high-impact review evidence | bounded positive `evidence_version` included in canonical JSON/SHA-256 | version range and digest-change regressions | implemented_on_active_pr |
| Preserve requested business-time bounds | distinct `requested_leave_start_on` and `requested_leave_end_on`, with end-before-start rejected | business-date/order regressions | implemented_on_active_pr |
| Coordinate staffing and benefits continuity without owning downstream execution | exact work-continuity, benefits-continuity, and return-to-work references/digests | reference/digest and immutable external-execution regressions | implemented_on_active_pr |
| Prove requester/reviewer separation from authoritative identities | different opaque actor references as an early guard; governed next action requires tenant-scoped re-resolution and distinct resolved identities before approval | actor-inequality and immutable next-action regressions | implemented_on_active_pr |
| Prevent syntax/digests from being mistaken for tenant/worker validity | `scope_verification_state=requires_authoritative_resolution`; next action requires re-resolution of every packet reference plus Person-to-Employment and active Assignment/Job/Position scope proof | immutable-state and next-action regressions | implemented_on_active_pr |
| Preserve accountable human authority | `human_confirmation_required=true`, `decision_authority=human_review_only`, `review_state=requires_human_review` | direct-construction and `dataclasses.replace(...)` regressions | implemented_on_active_pr |
| Prevent review evidence from masquerading as applied HRIS truth or owner execution | `mutation_state=not_authorized_to_apply`, `external_execution_state=not_authorized_to_execute` | immutable governance-state regressions | implemented_on_active_pr |
| Produce deterministic immutable correlation evidence | precision-preserving UTC canonical JSON and SHA-256 over exact UTF-8 bytes | timestamp and digest regressions | implemented_on_active_pr |
| Keep foreign dedicated-writer systems read-only | no provider credentials, foreign mutation, or cross-service application-table SQL; downstream actions only through published owner contracts | package architecture and ADR 0021 | implemented_on_active_pr |

## Protected-main boundary

Protected `develop` remains authoritative for integrated HRIS behavior. This active PR adds only a pre-mutation review evidence contract. It does not claim unmerged People mutation, payroll/benefits, identity, calendar, or other downstream execution capability.
