# Orgmetra external delivery receipt evidence

This package gives Orgmetra a small, value-minimized evidence object for the moment an
external transport reports that one outbox attempt was delivered.

It **does not** mark an outbox row delivered. A transport response is untrusted evidence.
The authoritative Orgmetra host must re-read the live tenant-scoped leased attempt, verify
the normalized receipt artifact, apply purpose-bound authorization, and persist its own
immutable audit/outbox evidence in the same governed completion transaction.

## What the evidence binds

`ExternalDeliveryReceiptEvidence` binds one exact:

- tenant, outbox delivery, and audit event;
- delivery target and attempt number;
- transport provider code;
- host-normalized opaque `transport_receipt:<UUIDv4>` reference;
- SHA-256 digest of the exact external receipt artifact;
- provider-reported delivery instant and host observation instant; and
- evidence version.

The canonical packet never carries the HR payload, destination address, credentials,
compensation, assessment/rating values, free-form model output, or an employment decision.

## Safe next action

Call `verify_exact_delivery_attempt(...)` only after resolving the authoritative current
outbox attempt. A successful match returns the canonical evidence digest for correlation;
it is still **not** permission to call `complete_outbox_delivery(...)`. The host must verify
the external receipt artifact against `transport_receipt_digest` and complete its normal
lease, authorization, audit, and persistence checks.

## Integrity model

The public evidence type is a tuple-backed immutable value. Ordinary mutation through
`setattr` or `object.__setattr__` fails. Canonical export also revalidates every
trust-bearing field, so copy helpers or low-level tuple construction cannot bypass the
fixed safety-state, shape, chronology, or identifier invariants. A separately constructed
receipt is still untrusted evidence and must independently match the authoritative exact
attempt plus the external receipt artifact before any governed completion can occur.

This is an application evidence contract, not a digital-signature scheme. Durable
cross-process authenticity and retention belong to the authoritative persistence and
audit/outbox boundary.

## Current integration status

This package is proposed by PR #151. Until that PR integrates into protected `develop`,
it is active-PR truth, not a commercially available protected-main capability.
