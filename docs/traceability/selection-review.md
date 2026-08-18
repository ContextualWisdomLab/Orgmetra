# Human selection-review packet traceability

## Maturity

**Active PR only.** This document describes the `feat/selection-review-packet` candidate branch. Protected `develop` does not contain this capability until the PR is integrated with fresh protected-head evidence.

## Requirement-to-evidence map

| Requirement | Owned object | Executable evidence |
|---|---|---|
| Prepare one candidate/Job/evidence set for accountable human review without copying candidate PII | `SelectionReviewPacket` opaque references | packet serialization regression proves the canonical payload contains governance metadata rather than candidate values |
| Preserve the exact reviewed evidence-set identity | `decision_evidence_set_reference`, `evidence_set_digest`, `evidence_version_code` | malformed namespace/version/digest regressions and independently recomputed SHA-256 packet digest |
| Keep high-impact decision authority human | `human_confirmation_required=True`, `review_state="requires_human_decision"`, governed `next_action` | direct-constructor regressions reject false/non-boolean confirmation, alternate state, and auto-decision copy |
| Treat model material only as draft evidence | paired `model_draft_reference`, `model_provenance_reference`, `model_output_status="untrusted_draft"` | regressions reject partial provenance, wrong namespaces, verified/authoritative status, and orphan status |
| Preserve tenant and accountable reviewer context | canonical operational tenant UUID plus `actor:` reviewer reference, purpose and reason | reserved/noncanonical UUID, malformed reference, and governance-code regressions |
| Produce stable immutable correlation evidence | canonical JSON plus SHA-256 | deterministic JSON and independent SHA-256 recomputation regression |
| Avoid host-time ambiguity | timezone-aware `generated_at`, canonical UTC rendering | naive/unknown-offset rejection and non-UTC-to-UTC canonicalization regression |
| Meet owned production coverage gate | `orgmetra_selection_review` | Selection Review Quality requires exact 100% statement and branch coverage |

## Authority boundary

The packet does not create or modify `selection_decision`, candidate, employment, Person, Job, Position, or Assignment rows. It does not authorize PII reads, call an assessment/model provider, or perform a hiring decision. The final selection decision remains an authoritative Orgmetra high-impact mutation requiring the existing evidence sealing, purpose-bound authorization, explicit human confirmation, and immutable audit/outbox boundaries.

No foreign dedicated-writer repository is mutated or queried through application-table SQL by this slice.
