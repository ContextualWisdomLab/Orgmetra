# ADR 0151: Govern external transport delivery receipt evidence before outbox completion

- **Status:** Proposed — active PR #151; not protected-main truth
- **Date:** 2026-08-29
- **Owners:** Orgmetra integration/audit boundary
- **Decision scope:** Evidence needed between an external transport response and an
  authoritative Orgmetra outbox completion transaction

## Context

Protected `develop` already persists immutable audit events and mutable outbox delivery
state. `complete_outbox_delivery(...)` correctly requires a current tenant-scoped live
lease, but the protected function does not itself require evidence from the external
transport that handled the attempt.

ADR 0006 identified external delivery receipts as subsequent work. No open Orgmetra PR was
found that owned a generic external outbox receipt contract; HR export PR #120 owns a
different one-time export-egress receipt boundary, and retry-policy PR #82 owns scheduling,
not transport acknowledgement.

## Decision

Add a standalone package that constructs a value-minimized
`ExternalDeliveryReceiptEvidence` and verifies exact-attempt correlation.

The evidence binds tenant/outbox/audit/target/attempt, a descriptive transport-provider
code, a host-normalized opaque receipt reference, SHA-256 of the exact external receipt
artifact, provider-reported delivery time, host observation time, and evidence version.

External transport evidence remains explicitly untrusted and carries
`not_authorized_to_mutate_delivery_state`. It excludes raw provider responses and protected
HR values. Canonical export revalidates every trust-bearing field, including instances
created through copy or low-level tuple construction, so those construction paths cannot
bypass fixed safety-state, shape, chronology, or identifier invariants. Separately
constructed receipts remain untrusted and still require authoritative exact-attempt and
artifact reconciliation.

Trust-bearing primitive values are accepted only as their exact built-in Python types,
not caller-defined subclasses whose equality or serialization behavior can be overridden.
Caller-owned aware datetimes are normalized once during construction into detached,
built-in UTC `datetime` values before the evidence object retains them. Later changes to a
caller-owned timezone provider therefore cannot rewrite the canonical JSON or digest.
Canonical export rejects low-level reconstructed evidence unless both stored timestamps
are already those frozen built-in UTC values. Exact-attempt verification likewise accepts
only the exact `ExternalDeliveryReceiptEvidence` type so a subclass cannot override the
returned digest or other trust behavior.

## Why not modify the outbox migration here

Open Orgmetra stacks already carry many provisional database migrations. Adding another
durable migration before the evidence contract is reviewed would increase collision and
restack risk. This slice establishes the package/API evidence boundary first. A subsequent
authoritative persistence change may bind the canonical receipt digest into outbox
completion after dependency order permits; it must not backfill or rewrite immutable audit
history.

## Consequences

- A caller can correlate a normalized external receipt to one exact current outbox attempt
  before authoritative completion.
- A receipt cannot by itself authorize `complete_outbox_delivery(...)`.
- Provider raw payloads, addresses, credentials, HR content, and employment decisions stay
  out of governance evidence.
- Receipt replay across retry attempts fails exact-attempt reconciliation.
- Mutable timezone providers and behavior-overriding primitive subclasses cannot remain
  embedded in canonical receipt evidence after construction.
- The contract remains independently extractable as an MSA/API boundary.

## Cryptographic and time references

SHA-256 is used only as deterministic artifact-correlation evidence, not as a signature or
proof of provider identity. NIST continues to list SHA-2/SHA-256 under FIPS 180-4 while a
revision of FIPS 180-4 has been announced. UTC `Z` rendering follows the RFC 3339 timestamp
form with RFC 9557's update to the semantics of `Z`; Orgmetra uses it here simply as a
canonical zero-offset representation.

See `docs/doctoring/outbox-delivery-receipt-references.md`.
