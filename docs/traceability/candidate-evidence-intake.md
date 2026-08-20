# Candidate evidence intake traceability

- **Maturity:** `implemented_on_active_pr`
- **Buyer capability:** Candidate Evidence workspace governance boundary
- **Owned contract:** `CandidateEvidenceIntakePacket`

| Requirement | Evidence |
|---|---|
| Correlate candidate evidence to the correct recruiting context | Canonical UUIDv4 tenant plus UUIDv4-backed candidate-profile, requisition and Job references; immutable next action requires every packet reference to be re-resolved within the exact tenant and candidate↔requisition↔Job correlation verified before sealing/review |
| Prevent cross-tenant evidence mixing | `test_tenant_scope.py` requires tenant-scoped resolution of every packet reference before correlation/provenance checks and authoritative sealing; UUID syntax alone is not tenant authority |
| Prevent public identity/reference fields from becoming a covert PII/value/correlation channel | `tenant_record_id` and every governed reference require canonical non-sentinel UUIDv4 identity; namespaced references also require their expected prefix. Human-readable/value-bearing suffixes, UUIDv1 timestamp/node metadata, and other UUID versions are rejected; `test_reference_privacy.py` covers the tenant identity plus every trust-reference field through builder and replacement paths |
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

The packet is correlation evidence, not proof of evidence truth, tenant ownership until authoritative resolution, lawful use, selection validity, fairness, policy execution, evidence sealing, or a final employment decision. UUIDv4 is an opacity/privacy constraint only; those claims require their own owner-bound evidence.