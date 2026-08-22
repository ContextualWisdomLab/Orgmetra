# HR Data Retention Review Traceability

Status: **active PR**. Protected `develop` does not contain this capability until this branch is independently reviewed and merged.

| Requirement | Executable evidence | Product state |
| --- | --- | --- |
| A retention date never becomes deletion authority | `test_retention_window_requires_continued_retention_and_never_authorizes_deletion`; `test_elapsed_retention_date_requires_authoritative_disposition_review` | active PR |
| Active legal hold blocks disposition review | `test_active_legal_hold_overrides_elapsed_retention_date`; `test_active_hold_requires_complete_versioned_hold_evidence` | active PR |
| Clear hold state cannot conceal contradictory hold evidence | `test_clear_hold_state_rejects_hidden_hold_evidence` | active PR |
| Requester and reviewer are distinct accountable actors | `test_rejects_same_requester_and_reviewer`; `test_replace_revalidates_governed_invariants` | active PR |
| Tenant and packet references are canonical opaque identifiers | `test_rejects_noncanonical_or_unreviewable_governance_values`; `test_rejects_wrong_namespace_malformed_or_non_uuid4_references` | active PR |
| Policy evidence is immutable and versioned | `test_correlation_digest_changes_when_governed_policy_evidence_changes` | active PR |
| Audit correlation is deterministic and value-minimized | `test_canonical_evidence_is_deterministic_value_minimized_and_redacted` | active PR |
| Canonicalization revalidates live trust-bearing state after low-level mutation | `test_canonicalization_rejects_reinjected_contradictory_hold_state`; `test_canonicalization_rejects_reinjected_non_utc_recorded_time` | active PR |
| System-recorded evidence cannot predate the claimed human-review business date | `test_rejects_recording_before_the_human_review_business_date` | active PR |
| Caller-defined Python scalar behavior cannot forge trust-bearing evidence | `test_rejects_noncanonical_or_unreviewable_governance_values` | active PR |
| Owned production code remains fully executable under tests | `HR Data Retention Quality` workflow with exact 100% statement/branch coverage | active PR; exact-head hosted evidence required |

## Authority boundary

The packet is pre-disposition evidence only. Before a later deletion/anonymization executor acts, the authoritative host must re-resolve current tenant/resource scope, applicable retention policy and jurisdiction, legal-hold state, reviewer authority, and immutable audit evidence. Canonical audit serialization revalidates the current packet fields but does not turn an in-memory Python object into the durable audit store; append-only audit/outbox persistence remains the authoritative durability boundary. No foreign dedicated-writer repository is mutated and no cross-service application-table SQL is introduced by this slice.
