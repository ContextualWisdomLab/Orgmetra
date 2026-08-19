# Orgmetra candidate evidence intake

This package defines a transport-neutral, reference-only packet for admitting candidate evidence into an accountable recruiting workflow without copying the candidate's evidence values into the governance envelope.

`CandidateEvidenceIntakePacket` binds one tenant, candidate profile, requisition, authoritative Job, versioned job requirements, evidence set, source-provenance manifest, handling policy, retention policy, accountable actor, purpose/reason, evidence-item count, and collection time. Every trust-bearing reference uses its expected namespace plus a canonical non-sentinel UUID suffix; content-bearing evidence also carries an independent lowercase SHA-256 digest.

The packet deliberately contains no candidate name, email, demographic attribute, assessment value, raw resume/document content, credential, or free-form model output. Human-readable or value-bearing reference suffixes are rejected so those fields cannot become a covert PII channel. UUID-backed candidate correlation remains sensitive metadata and must still be handled under the bound purpose, handling policy, retention policy, least-privilege authorization, export controls, and audit boundary. The ordinary object representation is fully redacted to avoid leaking correlation/evidence through logs or assertion failures.

The packet cannot represent approval. `human_confirmation_required` must be the boolean singleton `True`, `review_state` is fixed to `requires_human_review`, and the next action tells the operator to verify job relevance, source provenance, retention handling, and completeness before sealing the evidence set for accountable human review.

Canonical JSON and SHA-256 support immutable correlation only. They prove neither the truth of referenced evidence nor selection validity, fairness, legal compliance, authorization to use a particular evidence item, or final human approval. Authoritative persistence, evidence sealing, selection decisions, audit/outbox, and candidate-to-worker conversion remain separate Orgmetra boundaries.
