# Governed offer approval traceability

Status: **active PR / proposed capability**, not protected-main truth.

| Buyer requirement | Executable evidence | Contract outcome |
| --- | --- | --- |
| Exact selected-candidate scope | `test_rejects_bad_opaque_references`; canonical JSON test | Candidate is correlated only by a bounded opaque `candidate_profile:` reference. |
| Separate Job and Position | valid packet + optional-Position test | Job is mandatory; Position is separately named and optional rather than collapsed into Job. |
| Reviewed selection evidence | digest/reference validation tests | Selection decision identity and SHA-256 evidence are required. |
| Compensation/terms provenance without value duplication | value-free canonical JSON test; digest/reference validation tests | Package and terms are exact reference+digest pairs; salary/benefit values are absent. |
| Human accountability and separation of duties | same-reference rejection plus `test_actor_separation.py` | Requester/approver references differ locally, and approval requires tenant-scoped authoritative resolution proving distinct resolved actor identities. |
| No premature offer delivery | direct-constructor/replace fail-closed tests | State remains `requires_human_approval` and `not_authorized_to_send`. |
| Deterministic audit correlation | canonical JSON, fractional-second, timezone, SHA-256 tests | Canonical evidence is precision-preserving and deterministic. |
| Public API readability | module/class/function docstrings | Beginner-readable contract boundary is documented in source and package README. |

The SHA-256 packet digest proves only the exact canonical envelope bytes. It does not prove that
referenced evidence is substantively correct, that requester/approver resolve to different
identities, that compensation is lawful/fair, that a human approved the offer, or that an offer
was delivered. Authoritative actor resolution remains outside this evidence packet and is a
required pre-approval host check.
