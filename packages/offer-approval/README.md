# Orgmetra governed offer approval

This package creates a **value-free pre-send offer approval packet**. It is a governance envelope, not an offer engine and not an employment decision.

The packet binds one selected candidate to the exact requisition and authoritative Job, an optional exact Position, the reviewed selection-decision digest, compensation-package provenance, offer-terms provenance, and two accountable actor references. Identical requester and approver references are rejected as an early syntactic guard.

The envelope intentionally excludes candidate names, email addresses, demographic values, assessment scores, salary/benefit amounts, credentials, and free-form model output. `candidate_profile_reference` remains sensitive correlating metadata even though it is opaque. `tenant_record_id` follows Orgmetra's authoritative canonical non-sentinel operational UUID contract rather than imposing a second UUID-version rule in this leaf package. Packet-owned namespaced references remain canonical non-sentinel UUIDv4 values and require their expected namespace. UUIDv1 and other non-v4 reference suffixes are rejected so timestamp/node correlation metadata, names, compensation values, offer terms, and actor identities cannot be smuggled into packet-owned governance references. `reason_code` is likewise closed to the reviewed, value-free `selected_candidate_offer_review` code; arbitrary lower-snake-case text is rejected so the reason field cannot become a side channel for candidate, compensation, or offer-term values.

Trust-bearing tenant/reference/governance text is validated as exact built-in Python `str` before any UUID parsing, prefix/suffix parsing, closed-vocabulary membership, fixed-value comparison, or canonical serialization. Caller-defined string subclasses therefore cannot return safe parser/comparison results while retaining different underlying audit text.

Every packet also carries a bounded positive integer `evidence_version` (default `1`). It is serialized into canonical JSON, so changing the governed evidence version changes the packet SHA-256 digest. Zero, negative, boolean, textual, and values above `2147483647` fail closed. The field versions this immutable pre-send evidence envelope; it is not approval, delivery, or proof that referenced source versions were authoritatively resolved.

After successful construction, the packet binds its exact canonical JSON to a process-local HMAC issuance seal. `canonical_json()` and `sha256_digest()` recompute and verify that seal before returning evidence, so post-issuance mutation through low-level Python attribute operations fails closed even when the replacement value would otherwise pass field validation. Re-running `__post_init__()` cannot reissue or legitimize changed evidence, and removing the issuance seal also fails closed. This is **in-process mutation defense-in-depth only**: the random runtime seal is not a durable digital signature, external attestation, persistence mechanism, or substitute for immutable audit/outbox storage. Hosts that persist or transmit evidence must preserve the canonical JSON/digest and independently enforce their durable provenance controls.

A valid packet always remains `requires_human_approval` and `not_authorized_to_send`. Before approval, the host must re-resolve **every packet reference** within the exact `tenant_record_id` through its authoritative boundary so valid references from a foreign tenant cannot be mixed into the approval envelope. It must specifically re-resolve `requester_reference` and `approver_reference` and prove their resolved actor identities are distinct; opaque-reference inequality alone is not separation-of-duties evidence. The host must then verify Job/Position scope, selected-candidate evidence, compensation-package provenance, and offer-terms provenance before recording accountable human approval through the authoritative offer workflow and before communicating or executing the offer. UUIDv4 is only an opacity constraint for packet-owned references; tenant UUID generation/privacy policy remains owned by the authoritative HRIS boundary.

Canonical JSON and its SHA-256 digest support immutable audit correlation. They do not prove that the referenced evidence is true, that all references belong to the packet tenant, that actor identities are distinct, that compensation is lawful or fair, that an offer was approved, or that an offer was communicated.

## Example

```python
from datetime import datetime, timezone
from orgmetra_offer_approval import build_offer_approval_packet

packet = build_offer_approval_packet(
    tenant_record_id="11111111-1111-4111-8111-111111111111",
    offer_approval_reference="offer_approval:10000000-0000-4000-8000-000000000001",
    candidate_profile_reference="candidate_profile:10000000-0000-4000-8000-000000000002",
    requisition_reference="requisition:10000000-0000-4000-8000-000000000003",
    job_profile_reference="job_profile:10000000-0000-4000-8000-000000000004",
    position_record_reference="position_record:10000000-0000-4000-8000-000000000005",
    selection_decision_reference="selection_decision:10000000-0000-4000-8000-000000000006",
    selection_decision_digest="a" * 64,
    compensation_package_reference="compensation_package:10000000-0000-4000-8000-000000000007",
    compensation_package_digest="b" * 64,
    offer_terms_reference="offer_terms:10000000-0000-4000-8000-000000000008",
    offer_terms_digest="c" * 64,
    requester_reference="actor:10000000-0000-4000-8000-000000000009",
    approver_reference="actor:10000000-0000-4000-8000-00000000000a",
    purpose_code="offer_approval_review",
    reason_code="selected_candidate_offer_review",
    generated_at=datetime.now(timezone.utc),
)
```
