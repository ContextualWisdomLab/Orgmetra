# Candidate evidence intake traceability

- **Maturity:** `implemented_on_active_pr`
- **Buyer capability:** Candidate Evidence workspace governance boundary
- **Owned contract:** `CandidateEvidenceIntakePacket`

| Requirement | Evidence |
|---|---|
| Correlate candidate evidence to the correct recruiting context | Canonical tenant plus UUID-backed candidate-profile, requisition and Job references; immutable next action requires every packet reference to be re-resolved within the exact tenant and candidate↔requisition↔Job correlation verified before sealing/review |
| Prevent cross-tenant evidence mixing | `test_tenant_scope.py` requires tenant-scoped resolution of every packet reference before correlation/provenance checks and authoritative sealing; UUID syntax alone is not tenant authority |
| Prevent reference fields from becoming a covert PII/value channel | Every governed reference requires its expected namespace plus a canonical non-sentinel UUID suffix; human-readable/value-bearing suffixes are rejected |
| Preserve job-related evidence context | Versioned job-requirements reference + SHA-256 digest |
| Preserve evidence identity and source provenance without copying values | Evidence-set and source-provenance references + independent SHA-256 digests |
| Bind privacy/operational handling | Handling-policy and retention-policy references + independent SHA-256 digests |
| Version actor/purpose/reason evidence explicitly | `evidence_version` is a true positive integer through signed-int32 max and participates in canonical JSON/SHA-256; `test_evidence_version.py` proves presence, digest separation, bounds, and `dataclasses.replace(...)` revalidation |
| Preserve accountable collection context | Actor reference, fixed purpose, bounded reason, exact evidence-item count and precision-preserving UTC time |
| Prevent packet-as-decision misuse | Exact boolean human confirmation, immutable `requires_human_review` state and fixed next action |
| Prevent ordinary logs/assertions from leaking candidate correlation | generated dataclass repr disabled; `repr(packet)` is `CandidateEvidenceIntakePacket(<redacted>)`; repr-redaction regression |
| Preserve deterministic audit correlation | Canonical JSON + independently testable SHA-256 digest |
| Minimize candidate content exposure | No candidate name/email/demographic attribute/assessment value/raw evidence/credential/free-form model output in the packet |
| Keep service ownership boundaries intact | No database migration, no provider execution, no cross-service application-table SQL |

The packet is correlation evidence, not proof of evidence truth, tenant ownership until authoritative resolution, lawful use, selection validity, fairness, policy execution, evidence sealing, or a final employment decision. Those claims require their own owner-bound evidence.
