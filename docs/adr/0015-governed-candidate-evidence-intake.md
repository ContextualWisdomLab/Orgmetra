# ADR 0015: Govern candidate evidence intake as reference-only evidence

- **Status:** Proposed — active PR only
- **Date:** 2026-08-19

## Context

Orgmetra already owns candidate profiles, sealed selection-decision evidence, candidate-to-worker conversion, governed requisition review, and candidate-neutral interview planning. A buyer still needs a defensible intake boundary between receiving candidate-related material and later sealing or using it in a high-impact selection decision.

Copying resumes, assessment values, demographic attributes, or other candidate content into every workflow envelope increases privacy exposure and makes retention, provenance, and purpose control harder to audit. A nominally opaque reference is also unsafe if arbitrary human-readable/value-bearing suffixes are accepted: candidate names or other sensitive values can then be smuggled through reference fields. Ordinary object representations can create the same leak if they print sensitive correlation metadata in logs or assertion failures.

## Decision

Add a transport-neutral `CandidateEvidenceIntakePacket` that binds:

- canonical tenant identity and one UUID-backed opaque intake reference;
- UUID-backed candidate-profile, requisition, authoritative Job, job-requirements, evidence-set, provenance, handling-policy, retention-policy and actor references;
- independent SHA-256 digests where content drift matters;
- one accountable actor, bounded evidence-item count, fixed `candidate_evidence_intake` purpose, bounded reason metadata, and precision-preserving UTC collection time;
- mandatory human confirmation, immutable `requires_human_review` state, actionable next-step copy, and a fully redacted ordinary object representation.

Every reference must use the expected namespace plus a canonical non-sentinel UUID suffix. Human-readable/value-bearing suffixes are rejected fail-closed. The governance packet contains no candidate name, email, demographic attribute, assessment value, raw document content, credential, or free-form model output. UUID-backed candidate correlation remains sensitive metadata rather than anonymous data.

Canonical JSON plus SHA-256 provide immutable audit correlation but do not establish evidence truth, scientific validity, fairness, legal compliance, authorization, policy enforcement, or final approval.

## Consequences

### Positive

- Recruiting workflows can correlate candidate evidence to the exact Job/requisition and policy versions without duplicating candidate content.
- Reference fields cannot quietly become a human-readable PII/value channel.
- Source provenance, purpose-bound handling, and retention are explicit versioned evidence rather than prose-only assumptions.
- Ordinary logging/assertion formatting does not emit candidate correlation or evidence digests.
- The package remains standalone and MSA-friendly and performs no cross-service application-table SQL.

### Costs and constraints

- Hosts must use durable UUID-backed public identifiers rather than convenient semantic slugs inside governance references.
- The packet does not store raw candidate evidence, decide whether an item is lawfully usable, or prove the referenced policy was followed.
- UUID-backed candidate references are still sensitive correlating metadata and require least-privilege handling.
- Evidence sealing, authoritative selection decisions, immutable audit/outbox, deletion/retention execution, export controls, accommodations, adverse-impact monitoring, and jurisdiction-specific legal review remain separate obligations.
- This ADR remains proposed until its exact PR head merges into protected `develop`.

## References

See `docs/doctoring/candidate-evidence-intake-references.md`.
