# External delivery receipt traceability

**State:** Active PR #151 only. Protected `develop` does not yet expose this package.

| Requirement | Executable evidence | Production boundary |
| --- | --- | --- |
| Exact tenant/outbox/audit/target/attempt binding | `test_verifies_only_the_exact_outbox_attempt` | `verify_exact_delivery_attempt` |
| No HR payload, destination, or credential in the canonical evidence | `test_builds_value_minimized_untrusted_transport_evidence`; fixed-contract parametrization | `ExternalDeliveryReceiptEvidence` fixed safety fields |
| External receipt remains untrusted and non-authorizing | fixed-contract parametrization; hostile trust-state subclass regression | exact-type fixed-state validation |
| Opaque normalized receipt identity | receipt-reference parametrization | `_validate_receipt_reference` |
| Exact provider artifact correlation | digest parametrization | `_validate_digest`, `transport_receipt_digest` |
| Temporal evidence is detached from caller-owned timezone behavior and canonical UTC; observation cannot predate reported delivery | UTC precision, mutable-timezone, provider-failure, no-offset, and chronology regressions | `_freeze_timestamp`, `_canonical_timestamp`, `_validate_contract` |
| Trust-bearing text cannot retain behavior-overriding `str` subclasses | exact-attempt equality and fixed trust-state subclass regressions | exact built-in primitive validation |
| Receipt subclasses cannot override verification/digest behavior | `test_exact_attempt_verification_rejects_receipt_subclasses` | exact-type check in `verify_exact_delivery_attempt` |
| Retry replay cannot cross attempt boundaries | exact-attempt mismatch regression | `delivery_attempt_count` in reconciliation tuple |
| Copy/low-level reconstruction cannot bypass fixed safety/trust invariants | `test_copy_bypass_cannot_create_a_second_canonical_truth` | canonical export revalidation |
| Structural mutation is rejected | `test_evidence_is_structurally_immutable_after_construction` | tuple-backed evidence type |
| Exact owned statement/branch coverage | hosted `Outbox Delivery Receipt Quality` | pytest-cov gate at 100% |

## Upstream protected-main truth

- `database/migrations/0003_audit_outbox_persistence.sql` owns immutable audit events and
  durable outbox state.
- `database/migrations/0005_outbox_delivery_finalization.sql` owns live-lease completion
  and retry mutation.
- This PR does not change either migration and does not claim a durable receipt column.

## Downstream acceptance

Before any later durable receipt persistence or `delivered` transition is considered
commercial truth, the authoritative host must re-resolve the current tenant-scoped leased
attempt, verify the raw external artifact against the stored digest, preserve immutable
audit evidence, and pass the then-current exact-head migration/recovery/security/review
gates.
