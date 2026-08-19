# Human selection-review packet traceability

## Maturity

**Protected-main capability.** `SelectionReviewPacket` is present on protected `develop` as of merge commit `11a147a26f87e7a91a8fafc1e70dd0ee8a5ce70f`. This traceability document describes that integrated capability plus the active narrow hardening change that closes selection-review reason metadata to the reviewed vocabulary. It does not claim that a packet is itself a final employment decision.

## Requirement-to-evidence map

| Requirement | Owned object | Executable evidence |
|---|---|---|
| Prepare one candidate/Job/evidence set for accountable human review without copying candidate PII | `SelectionReviewPacket` UUID-backed opaque references | packet serialization regression proves the canonical payload contains governance metadata rather than candidate values |
| Prevent reference fields from becoming covert PII/value channels | expected namespace + canonical non-sentinel UUID suffix for candidate, Job, evidence set, reviewer and optional model evidence | semantic/sentinel/noncanonical suffix regressions across public construction and `dataclasses.replace(...)` |
| Prevent reason metadata from becoming a candidate/value side channel | closed reviewed `reason_code` vocabulary, initially `candidate_assessment` | `test_reason_vocabulary.py` rejects names, compensation values, protected-attribute labels, work-arrangement text, and mutation-by-copy bypass |
| Prevent routine logging/assertions from exposing sensitive correlation | generated dataclass repr disabled; `repr(packet)` is `SelectionReviewPacket(<redacted>)` | exact repr-redaction regression excludes tenant/candidate/reviewer/evidence digest |
| Preserve the exact reviewed evidence-set identity | `decision_evidence_set_reference`, `evidence_set_digest`, `evidence_version_code` | malformed namespace/version/digest regressions and independently recomputed SHA-256 packet digest |
| Keep high-impact decision authority human | `human_confirmation_required=True`, `review_state="requires_human_decision"`, governed `next_action` | direct-constructor regressions reject false/non-boolean confirmation, alternate state, and auto-decision copy |
| Treat model material only as draft evidence | paired UUID-backed `model_draft_reference`, `model_provenance_reference`, `model_output_status="untrusted_draft"` | regressions reject partial provenance, semantic/wrong namespaces, verified/authoritative status, and orphan status |
| Preserve tenant and accountable reviewer context | canonical operational tenant UUID plus UUID-backed `actor:` reviewer reference, fixed purpose, reviewed reason, and evidence version | reserved/noncanonical UUID, malformed reference, governance-code, and closed-reason regressions |
| Produce stable immutable correlation evidence | canonical JSON plus SHA-256 | deterministic JSON and independent SHA-256 recomputation regression |
| Avoid host-time ambiguity | timezone-aware `generated_at`, canonical UTC rendering | naive/unknown-offset rejection and non-UTC-to-UTC canonicalization regression |
| Meet owned production coverage gate | `orgmetra_selection_review` | Selection Review Quality requires exact 100% statement and branch coverage |

## Authority boundary

UUID-backed references remain sensitive correlating metadata rather than anonymous data. The packet does not create or modify `selection_decision`, candidate, employment, Person, Job, Position, or Assignment rows. It does not authorize PII reads, call an assessment/model provider, or perform a hiring decision. The final selection decision remains an authoritative Orgmetra high-impact mutation requiring the existing evidence sealing, purpose-bound authorization, explicit human confirmation, and immutable audit/outbox boundaries.

No foreign dedicated-writer repository is mutated or queried through application-table SQL by this slice.
