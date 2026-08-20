# Governed offer approval traceability

Status: **active PR / proposed capability**, not protected-main truth.

| Buyer requirement | Executable evidence | Contract outcome |
| --- | --- | --- |
| Exact selected-candidate scope | `test_rejects_bad_opaque_references`; canonical JSON test | Candidate is correlated only by a bounded opaque `candidate_profile:` reference. |
| Opaque trust-reference privacy | `test_rejects_uuid1_trust_references_through_direct_and_replace` | Every namespaced packet reference requires a canonical non-sentinel UUIDv4 suffix; UUIDv1 timestamp/node correlation and other UUID versions fail closed through direct construction and replacement. |
| Separate Job and Position | valid packet + optional-Position test | Job is mandatory; Position is separately named and optional rather than collapsed into Job. |
| Reviewed selection evidence | digest/reference validation tests | Selection decision identity and SHA-256 evidence are required. |
| Compensation/terms provenance without value duplication | value-free canonical JSON test; digest/reference validation tests | Package and terms are exact reference+digest pairs; salary/benefit values are absent. |
| Value-free reason metadata | `test_rejects_value_bearing_reason_codes_through_direct_and_replace` | `reason_code` is closed to reviewed `selected_candidate_offer_review`; arbitrary lower-snake-case candidate, compensation, or offer-term text fails closed. |
| Human accountability and separation of duties | same-reference rejection plus `test_actor_separation.py` | Requester/approver references differ locally, and approval requires tenant-scoped authoritative resolution proving distinct resolved actor identities. |
| High-impact evidence versioning | `test_evidence_version.py` | Bounded positive `evidence_version` is in canonical JSON, changes correlation SHA-256 across versions, and revalidates through mutation-by-copy. |
| No premature offer delivery | direct-constructor/replace fail-closed tests | State remains `requires_human_approval` and `not_authorized_to_send`. |
| Deterministic audit correlation | canonical JSON, fractional-second, timezone, evidence-version, SHA-256 tests | Canonical evidence is precision-preserving, versioned, and deterministic. |
| Public API readability | module/class/function docstrings | Beginner-readable contract boundary is documented in source and package README. |

The SHA-256 packet digest proves only the exact canonical envelope bytes. It does not prove that
referenced evidence is substantively correct, that requester/approver resolve to different
identities, that compensation is lawful/fair, that a human approved the offer, or that an offer
was delivered. Authoritative actor and source-evidence resolution remain outside this evidence
packet and are required pre-approval host checks.
