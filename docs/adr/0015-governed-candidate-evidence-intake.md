# ADR 0015: Govern candidate evidence intake as reference-only evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-19

## Context

Orgmetra already owns candidate profiles, sealed selection-decision evidence, candidate-to-worker conversion, governed requisition review, and candidate-neutral interview planning. A buyer still needs a defensible intake boundary between receiving candidate-related material and later sealing or using it in a high-impact selection decision.

Copying resumes, assessment values, demographic attributes, or other candidate content into every workflow envelope increases privacy exposure and makes retention, provenance, and purpose control harder to audit. At the same time, a bare file reference is insufficient: an accountable reviewer needs evidence that the intake was tied to the right candidate, requisition, authoritative Job and job requirements, source-provenance manifest, handling policy, retention policy, actor, purpose, and exact evidence-set version.

## Decision

Add a transport-neutral `CandidateEvidenceIntakePacket` that binds:

- canonical tenant identity and one opaque intake reference;
- one candidate profile, requisition, and authoritative Job reference;
- exact job-requirements reference plus SHA-256 digest;
- exact evidence-set and source-provenance references plus independent SHA-256 digests;
- exact handling-policy and retention-policy references plus independent SHA-256 digests;
- one accountable actor, bounded evidence-item count, fixed `candidate_evidence_intake` purpose, bounded reason metadata, and precision-preserving UTC collection time;
- mandatory human confirmation, immutable `requires_human_review` state, and actionable next-step copy.

The governance packet is reference-only. It contains no candidate name, email, demographic attribute, assessment value, raw document content, credential, or free-form model output. Direct construction and builder construction share the same fail-closed validation. Canonical JSON plus SHA-256 provide immutable audit correlation but do not establish evidence truth, scientific validity, fairness, legal compliance, authorization, or final approval.

## Consequences

### Positive

- Recruiting workflows can correlate candidate evidence to the exact Job/requisition and policy versions without duplicating candidate content.
- Source provenance, purpose-bound handling, and retention become explicit versioned evidence rather than prose-only assumptions.
- Downstream evidence sealing and human selection review can reject drift by reference/digest.
- The package remains standalone and MSA-friendly and performs no cross-service application-table SQL.

### Costs and constraints

- The packet does not store raw candidate evidence, decide whether an item is lawfully usable, or prove the referenced policy was followed.
- Opaque candidate references are still sensitive correlating metadata and require least-privilege handling.
- Evidence sealing, authoritative selection decisions, immutable audit/outbox, deletion/retention execution, export controls, accommodations, adverse-impact monitoring, and jurisdiction-specific legal review remain separate obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/candidate-evidence-intake-references.md`.
