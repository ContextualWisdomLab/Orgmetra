# Changelog

## Unreleased

- Add a governed, value-free pre-send offer approval packet.
- Require separate requester and approver identities and exact human approval.
- Bind selected-candidate, Job/optional Position, selection-decision, compensation-package, and offer-terms provenance without copying candidate or compensation values.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while packet-owned trust-reference suffixes remain canonical non-sentinel UUIDv4 and reject UUIDv1/non-v4 identity forms.
- Close `reason_code` to the reviewed value-free `selected_candidate_offer_review` contract so arbitrary candidate, compensation, or offer-term text cannot enter canonical evidence.
- Bind a bounded positive `evidence_version` into canonical JSON and SHA-256 correlation evidence so high-impact offer-review evidence versions are explicit and fail closed.
- Reject caller-defined string subclasses for tenant/reference/governance evidence before UUID parsing, reference parsing, reviewed comparisons, or canonical audit serialization.
- Detach `generated_at` into an immutable UTC instant before canonical JSON/SHA-256 generation and normalize timezone-provider, UTC-overflow, and post-construction timezone reinjection failures.
- Seal exact canonical packet bytes at issuance with a process-local HMAC and live identity registry; fail closed on post-issuance field mutation, seal removal, or attempted `__post_init__()` reissuance even after seal deletion.
- Preserve the same immutable issuance identity across shallow/deep copy and reject pickle serialization so copied or cross-process objects cannot become renewable evidence identities. This remains runtime defense-in-depth, not a durable signature or persistence boundary.
- Bind issuance to a one-time live constructor identity and require exact live issued identity before export, so slot-for-slot `object.__new__` clones cannot reuse copied seal bytes or mint replacement evidence.
- Make `Offer Approval Quality` retrigger on shared repository Python/test/clean-checkout configuration, with an executable regression preventing stale package-quality evidence after shared tooling changes.
- Keep every packet `requires_human_approval` and `not_authorized_to_send`.
