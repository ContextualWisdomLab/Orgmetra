# Changelog

## Unreleased

- Add a governed, value-free pre-send offer approval packet.
- Require separate requester and approver identities and exact human approval.
- Bind selected-candidate, Job/optional Position, selection-decision, compensation-package, and offer-terms provenance without copying candidate or compensation values.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while packet-owned trust-reference suffixes remain canonical non-sentinel UUIDv4 and reject UUIDv1/non-v4 identity forms.
- Close `reason_code` to the reviewed value-free `selected_candidate_offer_review` contract so arbitrary candidate, compensation, or offer-term text cannot enter canonical evidence.
- Bind a bounded positive `evidence_version` into canonical JSON and SHA-256 correlation evidence so high-impact offer-review evidence versions are explicit and fail closed.
- Keep every packet `requires_human_approval` and `not_authorized_to_send`.
