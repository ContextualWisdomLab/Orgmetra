# Governed offer approval traceability

Status: **active PR / proposed capability**, not protected-main truth.

| Buyer requirement | Executable evidence | Contract outcome |
| --- | --- | --- |
| Exact selected-candidate scope | `test_rejects_bad_opaque_references`; canonical JSON test | Candidate is correlated only by a bounded opaque `candidate_profile:` reference. |
| Authoritative tenant interoperability and packet-reference privacy | `test_tenant_identity_privacy.py`; `test_rejects_uuid1_trust_references_through_direct_and_replace` | `tenant_record_id` follows the canonical non-sentinel Orgmetra core operational-UUID contract; packet-owned namespaced references require canonical non-sentinel UUIDv4 and reject UUIDv1/non-v4 suffixes through construction and replacement paths. |
| Separate Job and Position | valid packet + optional-Position test | Job is mandatory; Position is separately named and optional rather than collapsed into Job. |
| Reviewed selection evidence | digest/reference validation tests | Selection decision identity and SHA-256 evidence are required. |
| Compensation/terms provenance without value duplication | value-free canonical JSON test; digest/reference validation tests | Package and terms are exact reference+digest pairs; salary/benefit values are absent. |
| Value-free reason metadata | `test_rejects_value_bearing_reason_codes_through_direct_and_replace` | `reason_code` is closed to reviewed `selected_candidate_offer_review`; arbitrary lower-snake-case candidate, compensation, or offer-term text fails closed. |
| Human accountability and separation of duties | same-reference rejection plus `test_actor_separation.py` | Requester/approver references differ locally, and approval requires tenant-scoped authoritative resolution proving distinct resolved actor identities. |
| High-impact evidence versioning | `test_evidence_version.py` | Bounded positive `evidence_version` is in canonical JSON, changes correlation SHA-256 across versions, and revalidates through mutation-by-copy. |
| Runtime issuance integrity | `test_rejects_post_issuance_runtime_evidence_mutation`, `test_rejects_attempt_to_reseal_mutated_runtime_evidence`, `test_rejects_reissue_after_seal_deletion_and_evidence_mutation`, copy/deepcopy/pickle regressions | Process-local HMAC plus live identity registration binds the issued object to its canonical bytes; seal deletion cannot reopen issuance, copy/deepcopy preserve the same immutable identity, and pickle fails closed rather than implying portable issuance provenance. |
| No premature offer delivery | direct-constructor/replace fail-closed tests | State remains `requires_human_approval` and `not_authorized_to_send`. |
| Deterministic audit correlation | canonical JSON, fractional-second, timezone, evidence-version, SHA-256 tests | Canonical evidence is precision-preserving, versioned, and deterministic. |
| Public API readability | module/class/function docstrings | Beginner-readable contract boundary is documented in source and package README. |

UUIDv4 is an opacity constraint for packet-owned trust references, not tenant authority. Tenant UUID generation/version/privacy policy remains owned by the authoritative HRIS boundary. Before approval, every packet reference must still resolve authoritatively inside the exact `tenant_record_id`; requester/approver identity separation must be proven after that resolution.

The SHA-256 packet digest proves only the exact canonical envelope bytes. The process-local HMAC/identity registry prevents silent runtime mutation/reissuance within one live process but is not portable persistence evidence: packet copying preserves the same object and pickle is intentionally rejected. These mechanisms do not prove that referenced evidence is substantively correct, that requester/approver resolve to different identities, that compensation is lawful/fair, that a human approved the offer, or that an offer was delivered. Authoritative actor/source-evidence resolution and durable immutable audit/outbox storage remain outside this evidence packet and are required pre-approval host controls.
