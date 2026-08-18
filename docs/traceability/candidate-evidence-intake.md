# Candidate evidence intake traceability

- **Maturity:** `implemented_on_active_pr`
- **Buyer capability:** Candidate Evidence workspace governance boundary
- **Owned contract:** `CandidateEvidenceIntakePacket`

| Requirement | Evidence |
|---|---|
| Correlate candidate evidence to the correct recruiting context | Canonical tenant, candidate-profile, requisition and Job references |
| Preserve job-related evidence context | Versioned job-requirements reference + SHA-256 digest |
| Preserve evidence identity and source provenance without copying values | Evidence-set and source-provenance references + independent SHA-256 digests |
| Bind privacy/operational handling | Handling-policy and retention-policy references + independent SHA-256 digests |
| Preserve accountable collection context | Actor reference, fixed purpose, bounded reason, exact evidence-item count and precision-preserving UTC time |
| Prevent packet-as-decision misuse | Exact boolean human confirmation, immutable `requires_human_review` state and fixed next action |
| Preserve deterministic audit correlation | Canonical JSON + independently testable SHA-256 digest |
| Minimize candidate content exposure | No candidate name/email/demographic attribute/assessment value/raw evidence/credential/free-form model output in the packet |
| Keep service ownership boundaries intact | No database migration, no provider execution, no cross-service application-table SQL |

The packet is correlation evidence, not proof of evidence truth, lawful use, selection validity, fairness, policy execution, evidence sealing, or a final employment decision. Those claims require their own owner-bound evidence.
