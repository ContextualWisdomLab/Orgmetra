# HR Data-Rights Request Traceability

## Status

`implemented_on_active_pr`. This document does not claim protected-main availability until the implementing PR is integrated.

## Buyer-visible requirement

An HRIS buyer needs a defensible way to record a privacy/data-rights request without putting the request body or HR values into durable routing evidence and without letting an intake record itself authorize disclosure, correction, deletion, restriction, export, or employment action.

## Contract mapping

| Requirement | Orgmetra boundary | Executable evidence | Maturity |
|---|---|---|---|
| Tenant- and Person-scoped request correlation | `HrDataRightsRequestPacket` tenant/request/Person references | canonical reference and tenant regressions | implemented_on_active_pr |
| Pseudonymous requester provenance | requester actor reference + identity evidence digest | identifying/malformed actor rejection; SHA-256 regression | implemented_on_active_pr |
| Policy-neutral request intent | closed `requested_action_code` routing vocabulary | access/correction/deletion/restriction acceptance plus command-like code rejection | implemented_on_active_pr |
| No request-time entitlement claim | fixed `requires_authoritative_policy_review` | direct-state-drift and all-intent regressions | implemented_on_active_pr |
| No disclosure/mutation authority | fixed `not_authorized_to_disclose` and `not_authorized_to_modify_hr_data` | direct construction and canonical-evidence regressions | implemented_on_active_pr |
| Value minimization | digests and opaque references only | canonical JSON forbidden-field regression | implemented_on_active_pr |
| Business/system chronology | `submitted_at` and later-or-equal `recorded_at` | chronology and exact-UTC regressions | implemented_on_active_pr |
| Runtime/canonical evidence integrity | exact primitives + issuance digest + verified snapshot export | hostile-string, copy, post-construction rewrite and checked-payload regressions | implemented_on_active_pr |
| Live request-reference consistency | tenant-qualified weak live-reference evidence registry | conflicting `dataclasses.replace()` RED plus exact-idempotent duplicate regression | implemented_on_active_pr |
| Installed-artifact evidence | exact wheel + isolated hash-pinned test toolchain | dedicated PR quality workflow | implemented_on_active_pr |

## Handoffs that remain authoritative

This package records request intake only. Fulfillment must re-enter Orgmetra's authoritative People/purpose-bound authorization, export-control, retention/legal-hold/disposition, and immutable audit/outbox boundaries as applicable. Identity must be re-resolved through the published Keyverse-facing adapter contract; no identity-provider credential or raw subject is stored here. No direct table access to another CWL service is permitted.

The live request-reference registry is process-local defense in depth, not a durable or distributed idempotency mechanism. A persistence host must enforce the tenant-qualified request reference/evidence binding transactionally with immutable audit/outbox evidence before replicas or restarts can be treated as authoritative.

## Standards truth

The current final NIST Privacy Framework input is Version 1.0. NIST Privacy Framework 1.1 was still an Initial Public Draft / forthcoming final when rechecked on 2026-08-23. GDPR Articles 15–17 are examples of request categories with legal conditions; they are not encoded as universal entitlement rules. See `docs/doctoring/hr-data-rights-request-references.md`.
