# Orgmetra product–technical gap baseline

- **Status:** Proposed
- **Protected evidence:** `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`
- **Active change:** PR #448, successor to PR #151
- **Scope:** Orgmetra-owned external delivery receipt evidence; no claim of protected or released capability

## Product and architecture bindings

| Evidence | Current binding |
| --- | --- |
| PRD | `docs/PRD.md` defines governed workforce operations and evidence-bearing decisions. |
| TRD | `docs/TRD.md` defines fail-closed application and persistence boundaries. |
| UML | `docs/UML.md` supplies the protected interaction vocabulary; ADR 0151 adds an untrusted receipt evidence value before authoritative completion. |
| ERD | `docs/ERD.md` remains unchanged because this Proposed slice adds no durable receipt column. |
| Context Map | `ARCHITECTURE.md` and ADR 0002 retain Orgmetra domain truth; external transport is an ACL input, not an authority. |
| Decision | `docs/adr/0151-governed-external-delivery-receipt.md` owns the receipt invariant and successor lineage. |
| Verification | `docs/traceability/outbox-delivery-receipt.md` binds requirements to package tests and canonical Foundation CI. |

## Current gaps and actions

| Gap ID | Buyer-visible gap and risk | Current evidence | Action and acceptance | Status |
| --- | --- | --- | --- | --- |
| ORGMETRA-OUTBOX-RECEIPT-01 | Protected Orgmetra cannot yet present value-minimized, exact-attempt evidence that an external transport reported delivery. Without this boundary, operators and diligence reviewers cannot distinguish transport acknowledgement from authority to mutate delivery state. | Protected `develop` owns audit/outbox persistence but not the proposed package. PR #448 carries the complete valid PR #151 package/docs/tests delta and integrates it into canonical Foundation CI. | Keep the evidence non-authorizing; prove exact tenant/outbox/audit/target/attempt correlation, canonical UTC and SHA-256 artifact correlation, 100% owned statement/branch coverage, terminal Security/SAST/CodeQL/Foundation Checks, independent review, and ordinary protected integration. Durable receipt persistence remains a later separately governed migration. | Proposed — source carryover and CI ownership repaired; hosted exact-head checks and independent approval pending. |

## Domain boundary and invariant

The Integration/Audit bounded context owns the
`ExternalDeliveryReceiptEvidence` value object. External transport input crosses an
anti-corruption boundary and remains `untrusted_transport_evidence`. Its invariant is
that successful exact-attempt reconciliation returns correlation evidence only; it never
authorizes `complete_outbox_delivery(...)`. The authoritative Orgmetra host must
re-resolve the live tenant-scoped lease, verify the raw artifact digest, apply
purpose-bound authorization, and persist immutable audit/outbox evidence atomically.
