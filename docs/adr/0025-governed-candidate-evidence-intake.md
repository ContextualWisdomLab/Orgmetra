# ADR 0025: Govern candidate evidence intake as reference-only evidence

- **Status:** Accepted on protected `develop`
- **Date:** 2026-08-19

## Context

Orgmetra already owns candidate profiles, sealed selection-decision evidence, candidate-to-worker conversion, governed requisition review, and candidate-neutral interview planning. A buyer still needs a defensible intake boundary between receiving candidate-related material and later sealing or using it in a high-impact selection decision.

Copying resumes, assessment values, demographic attributes, or other candidate content into every workflow envelope increases privacy exposure and makes retention, provenance, and purpose control harder to audit. A nominally opaque packet-owned reference is also unsafe if arbitrary human-readable/value-bearing suffixes are accepted: candidate names or other sensitive values can then be smuggled through reference fields. UUIDv1 adds a subtler correlation channel for packet-owned references because timestamp/node-derived metadata can be embedded in an otherwise canonical UUID. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package must accept the canonical non-sentinel operational UUID contract owned by that boundary rather than silently imposing a second version policy. Ordinary object representations can create the same leak if they print sensitive correlation metadata in logs or assertion failures. Canonical UUID syntax also does not prove tenant ownership, so a valid reference from another tenant must not be accepted as authoritative evidence merely because its shape is correct.

## Decision

Add a transport-neutral `CandidateEvidenceIntakePacket` that binds:

- canonical non-sentinel Orgmetra tenant identity and one UUIDv4-backed opaque intake reference;
- UUIDv4-backed candidate-profile, requisition, authoritative Job, job-requirements, evidence-set, provenance, handling-policy, retention-policy and actor references;
- independent SHA-256 digests where content drift matters;
- one accountable actor, bounded evidence-item count, fixed `candidate_evidence_intake` purpose, bounded reason metadata, and precision-preserving UTC collection time;
- mandatory human confirmation, immutable `requires_human_review` state, actionable next-step copy, and a fully redacted ordinary object representation.

`tenant_record_id` must be canonical and non-sentinel under Orgmetra's authoritative operational UUID contract. The package does not reinterpret its UUID version because tenant identity generation and migration policy belong to the authoritative HRIS boundary. Packet-owned namespaced trust references separately require canonical non-sentinel UUIDv4 and the expected prefix. Human-readable/value-bearing suffixes, UUIDv1, and other non-v4 suffixes are rejected fail-closed for those references. Before sealing or accountable review, the host must re-resolve **every packet reference** within the exact `tenant_record_id` through its authoritative boundary, then prove candidate↔requisition↔Job correlation and verify provenance, handling, retention, and completeness. UUID syntax is only an early shape/opacity guard; it is not tenant authority or relationship evidence. The governance packet contains no candidate name, email, demographic attribute, assessment value, raw document content, credential, or free-form model output. UUID-backed tenant and candidate correlation remain sensitive metadata rather than anonymous data.

Canonical JSON plus SHA-256 provide immutable audit correlation but do not establish evidence truth, scientific validity, fairness, legal compliance, authorization, policy enforcement, or final approval.

## Consequences

### Positive

- Recruiting workflows can correlate candidate evidence to the exact Job/requisition and policy versions without duplicating candidate content.
- Packet-owned reference fields cannot quietly become a human-readable PII/value channel or UUIDv1 timestamp/node correlation channel, while the leaf package remains interoperable with authoritative Orgmetra tenant UUIDs.
- Cross-tenant evidence mixing is fail-closed at the host sealing/review boundary because every packet reference must resolve within the packet tenant.
- Source provenance, purpose-bound handling, and retention are explicit versioned evidence rather than prose-only assumptions.
- Ordinary logging/assertion formatting does not emit candidate correlation or evidence digests.
- The package remains standalone and MSA-friendly and performs no cross-service application-table SQL.

### Costs and constraints

- Packet-owned trust references must use durable UUIDv4-backed public identifiers and must be authoritatively resolved in the exact tenant before use. Tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.
- The packet does not store raw candidate evidence, decide whether an item is lawfully usable, or prove the referenced policy was followed.
- UUID-backed tenant and candidate references are still sensitive correlating metadata and require least-privilege handling.
- Evidence sealing, authoritative selection decisions, immutable audit/outbox, deletion/retention execution, export controls, accommodations, adverse-impact monitoring, and jurisdiction-specific legal review remain separate obligations.
- This ADR records the accepted protected-`develop` candidate-evidence intake boundary; later sealing, selection, retention, and legal-use obligations remain separate authorities.

## References

See `docs/doctoring/candidate-evidence-intake-references.md`.
