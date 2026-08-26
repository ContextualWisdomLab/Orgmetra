# Changelog

All notable package-local changes are documented here. Protected-repository release truth remains the root Orgmetra release process.

## 0.2.0 — Unreleased stacked execution

### Added

- `HrDataExportExecutionVerification` for fresh export-specific tenant/resource/field/format/destination authorization plus human-approval, retention and legal-hold evidence.
- Bounded `HrDataExportArtifact` with exact immutable bytes, reviewed field tuple, exact media type, SHA-256 and hard 10 MiB budget.
- `HrDataExportAuditReceipt` requiring value-minimized immutable audit evidence to bind the exact reviewed/export-authorized artifact **before** outbound egress.
- `HrDataExportEgressReceipt` for host-owned `authenticated_one_time_download` evidence with mandatory one-time-use enforcement.
- `execute_reviewed_hr_export(...)` orchestration with authorization-freshness checks before protected reads, after materialization and after audit, plus exact delivery-time authorization-window validation on the returned egress receipt.
- Mandatory `HrDataExportEgressPort.reconcile_one_time_download(...)` contract for authoritative lookup of an existing ambiguous one-time delivery without republishing bytes.
- `HrDataExportDeliveryIndeterminateError` so unreconciled post-publication outcomes are explicitly non-retryable rather than indistinguishable from pre-side-effect failures.
- Externally sealed `HrDataExportExecutionReceipt` containing only correlations, evidence digests, artifact size, audit/egress references and chronology—never raw HR values.
- Adversarial execution tests for scope drift, policy/legal-hold blocks, authorization TOCTOU, artifact mismatch/size, audit binding, egress binding, one-time semantics, ambiguous delivery reconciliation and post-issuance tampering.

### Security

- Retrieval/review evidence is never treated as export authority; execution requires a fresh export-specific authority decision and accountable human approval.
- Raw HR values cannot reach the egress port before exact artifact validation and committed pre-delivery audit evidence.
- Authorization expiry during materialization or audit latency blocks later audit/egress as appropriate. The one-time host receipt must prove that actual delivery occurred before expiry; later receipt-processing latency does not turn an already completed authorized delivery into a retryable failure.
- Delivery at or after the half-open authorization expiry instant fails receipt validation even when the egress call began earlier.
- An exception or unusable receipt after the publication call never triggers a second publication. Orgmetra performs reconciliation-only lookup under the same execution/audit/artifact correlation; missing or invalid reconciliation raises `HrDataExportDeliveryIndeterminateError` with a do-not-republish contract.
- A post-publication clock failure is likewise treated as an indeterminate side-effect outcome rather than a safe retry opportunity.
- Parent `HrDataExportReviewPacket` creation evidence is inherited with the process-local external seal repair; valid-looking low-level scope rewrites fail closed.

## 0.1.0 — Unreleased parent review

### Added

- Value-minimized `HrDataExportReviewPacket` for pre-export HR data review.
- Exact tenant/resource/authorization provenance correlation without HR field values.
- Explicit bounded field minimization, requester/reviewer separation, closed reason/format/destination vocabularies, and human-review-required state.
- UTC timestamp detachment from caller-controlled timezone providers and serialization-time integrity revalidation.
- Redacted representation plus deterministic canonical JSON/SHA-256 audit correlation.
- Adversarial tests and exact 100% owned statement/branch coverage gate.

### Security

- The packet is permanently `not_authorized_to_export` and `requires_authoritative_resolution`; it cannot itself be used as an export capability.
- Trust-bearing primitive subclasses and packet subclasses fail closed before governance comparisons or canonical serialization.
- Creation-time canonical evidence is sealed in a process-local weak registry outside packet-writable state; durable cross-process uniqueness and replay protection remain authoritative persistence responsibilities.
