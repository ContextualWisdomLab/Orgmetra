# HR data export control traceability

## State

- Protected `develop` truth at slice start: `9e3e4847510e1e612b48474ba42b177b8ed824df`.
- Accepted architecture: ADR 0008 purpose-bound PII authorization; its explicit limitation says export-control workflow remains a subsequent Orgmetra slice.
- This document: **active PR**, not protected-main truth until merge.
- Dedicated-writer dependencies: Keyverse and every other CWL service remain read-only. No foreign repository, workflow, ref, PR state, setting, or application table is mutated or queried directly by this slice.

## Buyer requirement → control → executable evidence

| Requirement | Orgmetra control | Evidence |
| --- | --- | --- |
| Necessary PII stays usable only for an approved purpose | Packet binds `purpose_code=hr_data_export_review` to opaque authorization evidence and exact requested field names; actual values remain outside the packet | `test_packet_is_value_minimized_deterministic_and_redacted`; dedicated quality gate |
| Tenant/resource scope cannot drift | Canonical operational tenant UUID plus resource-kind-bound opaque UUIDv4 reference | tenant/reference adversarial parameter matrix |
| No wildcard/bulk field escalation | Non-empty exact tuple, max 64, sorted, unique, descriptive field codes | `test_requested_fields_are_bounded_sorted_unique_exact_tuple` |
| Human accountability before egress | Requester and reviewer must be distinct; packet remains `human_review_required=True` | requester/reviewer and direct-construction regressions |
| Authorization evidence is immutable/correlatable | Opaque `authorization_decision:` reference, lowercase SHA-256 digest, bounded policy version | authorization provenance regressions |
| One reviewed correlation cannot be rewritten into a second valid-looking truth | Creation-time canonical evidence is sealed in a process-local weak registry outside packet-writable state; serialization requires the live packet to match that external seal | `test_canonicalization_rejects_valid_post_issuance_field_scope_rewrite`; serialization-integrity gate |
| The review artifact is not itself an export capability | Fixed `requires_authoritative_resolution` + `not_authorized_to_export`; authenticated one-time download is only a reviewed destination class, not an implemented transfer | direct-construction and post-construction tampering regressions |
| Runtime polymorphism cannot forge audit evidence | Trust-bearing text/int primitives and packet type fail closed on subclasses | `ForgedStr`, `ForgedInt`, packet-subclass regressions |
| Recorded chronology cannot change after validation | Caller timezone resolved once, detached into built-in UTC, and revalidated before serialization | mutable/exploding/offsetless timezone and serialization-integrity regressions |
| Evidence does not leak HR values through logs | Packet repr is fixed redacted text and canonical JSON contains field names/provenance only | deterministic/redaction regression |
| Owned code remains exactly covered | Dedicated workflow requires 100% statement and branch coverage on exact PR head | `.github/workflows/hr-data-export-quality.yml` |

The process-local creation seal is explicitly defense in depth. Durable uniqueness, replay/idempotency, cross-process authorization and immutable audit/outbox evidence remain authoritative host/persistence responsibilities; the in-process weak registry is not a distributed lock or database constraint.

## Execution boundary

The next execution slice, if/when independently prioritized, must re-resolve through the authoritative People authorization boundary immediately before materializing values. It must bind authorization freshness, requester/reviewer identities, tenant, resource, purpose, exact fields, export format, one-time delivery, retention/deletion, and immutable audit/outbox evidence. This packet must not be upgraded into a bearer capability or used to justify direct cross-service application-table SQL.

## Supersession rule

If the protected People/Keyverse authorization contract changes before this PR merges, this slice must adapt to the fresh protected contract and rerun exact-head evidence. No predecessor, status-only, model-only, skipped, cancelled, neutral, absent, queued, or stale workflow result is passing evidence.
