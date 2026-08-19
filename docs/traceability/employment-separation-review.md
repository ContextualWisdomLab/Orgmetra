# Employment separation review traceability

Status: `implemented_on_active_pr` only. This document does not describe protected-`develop` capability until the owning PR is integrated.

| Requirement | Implemented boundary | Evidence | Maturity |
|---|---|---|---|
| Correlate one proposed separation to authoritative worker scope without copying worker values | `EmploymentSeparationReviewPacket` binds Person, Employment and exact active Assignment/Job/Position snapshot references/digest | valid-packet and canonical payload regressions | implemented_on_active_pr |
| Prevent syntactically valid references from being mistaken for authoritative tenant/worker scope | governed next action requires every packet reference to be re-resolved within exact `tenant_record_id`, proves Person-to-Employment binding and each active Assignment/Job/Position in the bound snapshot before approval | `test_next_action_requires_tenant_scoped_reference_resolution_and_worker_binding` plus immutable `next_action` direct-construction regression | implemented_on_active_pr |
| Require reviewed separation policy/process | exact policy/process references plus independent SHA-256 digests | malformed reference/digest and deterministic evidence regressions | implemented_on_active_pr |
| Version high-impact actor/purpose/reason evidence | bounded positive `evidence_version` included in canonical JSON/SHA-256 | version presence, range and digest-change regressions | implemented_on_active_pr |
| Coordinate final-pay and benefits without copying amounts | value-free final-pay/benefits handoff references and digests; `contains_compensation_values=false` | payload-minimization and direct-construction regressions | implemented_on_active_pr |
| Coordinate identity/access without owning identity execution | access-deprovisioning plan reference/digest; `external_execution_state=not_authorized_to_execute` | direct-construction fail-closed regression | implemented_on_active_pr |
| Coordinate organizational-property and continuity work | asset-return, knowledge-transfer and communication plan references/digests | namespace/digest validation regressions | implemented_on_active_pr |
| Prevent sensitive separation narrative from becoming portable governance data | no free-form case narrative; reason is one reviewed operational category | sensitive/unreviewed reason rejection and privacy-flag regressions | implemented_on_active_pr |
| Preserve accountable human authority | distinct requester/reviewer, mandatory human confirmation, human-only decision authority, review required | actor-separation and immutable-governance regressions | implemented_on_active_pr |
| Prevent review evidence from masquerading as live HRIS truth or completed owner execution | `requires_authoritative_resolution`, `not_authorized_to_apply`, `not_authorized_to_execute` | direct construction and `dataclasses.replace(...)` regressions | implemented_on_active_pr |
| Produce deterministic immutable correlation evidence | canonical precision-preserving UTC JSON and SHA-256 over exact UTF-8 bytes | canonicalization/digest regression | implemented_on_active_pr |
| Keep foreign dedicated-writer systems read-only | no provider credentials, no foreign mutation, no cross-service application-table SQL; downstream work only through published owner contracts | package architecture and ADR 0020 | implemented_on_active_pr |

## Protected-main boundary

Protected `develop` remains authoritative for currently integrated HRIS behavior. This active PR adds only a pre-mutation evidence contract. It does not integrate or claim the unmerged People mutation, Job Analysis, payroll/final-pay, benefits, or identity execution capabilities of other lanes/repositories.
