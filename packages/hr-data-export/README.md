# Orgmetra HR Data Export Control

This package defines a **pre-export review packet** for HR data egress. It is intentionally narrower than an export service: the packet contains no employee or candidate field values and is permanently marked `not_authorized_to_export` until a later execution boundary re-resolves authoritative authorization and records accountable human approval.

## What this slice protects

`HrDataExportReviewPacket` binds one tenant, one opaque HR resource, one purpose-bound authorization evidence reference and SHA-256 digest, one reviewed field subset, one requester, one distinct reviewer, one export format, one delivery class, one evidence version, and one recorded instant. Trust-bearing strings and integers use exact built-in runtime types so caller-defined equality, hashing, ordering, or parser behavior cannot make validation disagree with canonical audit evidence. Recorded time is detached from caller-controlled `tzinfo` behavior and stored as built-in UTC.

The packet also seals its creation-time canonical evidence in a process-local weak registry outside packet-writable state. That defense prevents low-level `object.__setattr__` rewriting of one valid reviewed field scope into a second valid-looking audit truth. The registry is **defense in depth only**: durable uniqueness, replay/idempotency, cross-process authorization, and immutable audit/outbox persistence remain responsibilities of the authoritative host transaction.

The requested field tuple is explicit, sorted, unique, non-empty, and capped at 64 names. There is no wildcard. Supported review reasons are `employee_access_request`, `regulatory_disclosure`, and `contractual_hr_export`; formats are `json` and `csv`; the only delivery class in this slice is `authenticated_one_time_download`.

## What this slice does not do

The packet does **not** fetch HR values, create a downloadable archive, authorize a network transfer, write Keyverse state, read another service's application tables, or claim compliance/certification. It consumes only opaque authorization provenance. Before any data leaves the owning People boundary, the host must re-resolve the authenticated actor, exact resource and tenant, purpose-bound policy, exact field subset, authorization freshness, and accountable human approval, then write immutable audit/outbox evidence through the owning Orgmetra contract.

That separation is deliberate: accepted ADR 0008 makes purpose one authorization attribute rather than blanket access, and identifies export-control workflow as a separate Orgmetra responsibility. This package operationalizes the review portion without weakening that boundary.

## Customer/operator next action

When an export request reaches this stage, review the listed field names and reason, verify the requester and reviewer are different accountable actors, then re-resolve the authorization evidence through the authoritative People authorization boundary. Only a later explicitly governed execution slice may generate a one-time authenticated download, and it must fail closed if tenant, resource, purpose, field scope, policy version, approval evidence, or freshness has drifted.

## Verification

Run:

```bash
PYTHONPATH=packages/hr-data-export/src python -m pytest \
  -c packages/hr-data-export/pyproject.toml packages/hr-data-export/tests
```

The dedicated `HR Data Export Quality` workflow checks the exact pull-request head, compiles the package and tests, requires exact 100% statement/branch coverage, and requires a clean checkout afterward. Security, SAST, Foundation, and Recovery workflows remain independent applicable evidence.

## Status

This package is **active-PR implementation**, not protected-`develop` truth, until its pull request is merged through normal protection and independent review. The broader export bundle/delivery, retention/deletion, policy administration, and persistent audit workflow remain out of scope for this bounded slice.
