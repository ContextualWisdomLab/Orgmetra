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
material masquerade as an approved offer.

ISO 30405:2023 provides current recruitment guidance across planning, assessment, employment,
stakeholder management, and review. EEOC guidance on tests and selection procedures emphasizes
job-related use and employer responsibility for selection procedures. Those sources support a
conservative evidence-and-human-review boundary; they do not by themselves certify this package
or decide the legality of any offer.

## Decision

Orgmetra will expose `OfferApprovalPacket` as value-free review evidence only.

The packet binds opaque references for the candidate profile, requisition, Job, optional
Position, selection decision, compensation package, and offer terms. Decision/package/terms
artifacts are independently SHA-256 bound. Requester and approver must be different actors.

The packet must not contain candidate PII, compensation values, assessment scores, or
free-form model output. Direct construction and `dataclasses.replace(...)` revalidate all
trust-bearing invariants.

Every packet is fixed to:

- purpose `offer_approval_review`;
- `human_confirmation_required=True`;
- decision authority `human_approval_only`;
- review state `requires_human_approval`;
- delivery state `not_authorized_to_send`.

Canonical JSON and SHA-256 are audit-correlation evidence only. The packet does not approve,
communicate, send, execute, or persist an offer.

## Consequences

A buyer can review one deterministic, PII-minimized envelope before an offer moves to the
authoritative offer workflow. Compensation values stay in their purpose-bound owner boundary,
while Orgmetra keeps exact provenance references and human accountability.

Downstream offer persistence/execution must independently enforce authorization, evidence
versioning, idempotency where applicable, and immutable audit/outbox evidence. This ADR remains
proposed active-PR truth until integrated into protected `develop`.

## References

See `docs/doctoring/offer-approval-references.md`.
