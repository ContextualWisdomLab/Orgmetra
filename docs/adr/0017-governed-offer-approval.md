# ADR 0017: Governed offer approval evidence

- Status: Proposed — active PR only
- Date: 2026-08-19
- Scope: Talent Acquisition offer review

## Context

Protected `develop` can govern candidate, requisition, selection, and employment evidence,
but it does not yet expose a bounded pre-send contract proving that a proposed offer is tied
to the selected candidate, authoritative Job/optional Position, reviewed selection decision,
compensation-package provenance, offer-terms provenance, and accountable human approval.

Offer review is high-impact employment workflow. A governance envelope must not become an
alternate decision authority, a salary-value cache, or a channel that lets generated/model
material masquerade as an approved offer. Different opaque requester/approver references also
do not prove that the authoritative actor boundary resolves them to different people.

ISO 30405:2023 provides current recruitment guidance across planning, assessment, employment,
stakeholder management, and review. EEOC guidance on tests and selection procedures emphasizes
job-related use and employer responsibility for selection procedures. Those sources support a
conservative evidence-and-human-review boundary; they do not by themselves certify this package
or decide the legality of any offer.

## Decision

Orgmetra will expose `OfferApprovalPacket` as value-free review evidence only.

The packet binds opaque references for the candidate profile, requisition, Job, optional
Position, selection decision, compensation package, and offer terms. Decision/package/terms
artifacts are independently SHA-256 bound. Identical requester/approver references are rejected
as an early syntactic guard. Before approval, the host must re-resolve both actor references
within the exact packet tenant through the authoritative actor boundary and reject approval
unless the resolved actor identities are distinct. Reference inequality alone is not
separation-of-duties evidence.

The packet must not contain candidate PII, compensation values, assessment scores, or
free-form model output. The `reason_code` field is not free-form metadata: it is closed to the
reviewed value-free `selected_candidate_offer_review` code so syntactically valid text cannot
smuggle candidate, compensation, or offer-term values into canonical evidence. Direct
construction and `dataclasses.replace(...)` revalidate all trust-bearing invariants.

Every packet is fixed to:

- purpose `offer_approval_review`;
- reviewed reason `selected_candidate_offer_review`;
- bounded positive integer `evidence_version` (default `1`), included in canonical JSON/SHA-256;
- `human_confirmation_required=True`;
- decision authority `human_approval_only`;
- review state `requires_human_approval`;
- delivery state `not_authorized_to_send`.

`evidence_version` accepts only real integers from `1` through `2147483647`; booleans, text,
zero, negative values, and overflow values fail closed. It versions the immutable pre-send
evidence envelope and does not itself prove source-version resolution, approval, or delivery.

Canonical JSON and SHA-256 are audit-correlation evidence only. The packet does not approve,
communicate, send, execute, persist an offer, or prove authoritative actor identity.

## Consequences

A buyer can review one deterministic, PII-minimized envelope before an offer moves to the
authoritative offer workflow. Compensation values stay in their purpose-bound owner boundary,
while Orgmetra keeps exact provenance references, evidence version, and human accountability.
Requester/approver separation is proven only after tenant-scoped authoritative actor resolution.
New offer-review reason categories require an explicit contract change and regression evidence
rather than accepting arbitrary caller text.

Downstream offer persistence/execution must independently enforce authorization, source-evidence
resolution, idempotency where applicable, and immutable audit/outbox evidence. This ADR remains
proposed active-PR truth until integrated into protected `develop`.

## References

See `docs/doctoring/offer-approval-references.md`.
