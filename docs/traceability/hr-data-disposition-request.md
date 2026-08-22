# HR Data Disposition Request Traceability

## Truth-state boundary

| State | Truth in this stack |
|---|---|
| Protected `develop` | No HR data disposition execution-request package is shipped. |
| Parent PR #76 | Adds `HrDataRetentionReviewPacket`, which can conclude only that an elapsed due date requires authoritative disposition review and remains `not_authorized_to_delete`. |
| This active PR | Adds a separate, non-executing `HrDataDispositionExecutionRequest` contract. |
| Planned | Durable executor, purpose-bound execution authorization, immutable audit/outbox persistence, idempotent deletion/pseudonymization implementation, recovery, and storage-owner sanitization evidence integration. |
| Out of scope | Automatic deletion from a due date; direct foreign-service table mutation; treating application deletion as media sanitization; autonomous LLM disposition decisions. |

## Requirement-to-evidence map

| Requirement | Executable evidence |
|---|---|
| Only post-due reviewed records may enter a disposition request | `test_rejects_invalid_chronology_hold_or_scalar_evidence`, `test_replace_cannot_bypass_post_due_or_actor_separation` |
| A legal hold must be clear before request construction | `test_rejects_invalid_chronology_hold_or_scalar_evidence` |
| Upstream review must still be non-authorizing | `test_rejects_malformed_or_unreviewed_text_evidence` for `upstream_retention_window_state` and `upstream_disposition_authorization_state` |
| Requester and reviewer are distinct | `test_requires_distinct_requester_and_reviewer` and replacement-path regression |
| Tenant/resource/policy/review evidence is opaque, canonical, and value-minimized | malformed text/reference/digest regressions plus `test_request_is_explicitly_non_authorizing_and_value_minimized` |
| Caller-defined scalar behavior cannot forge validation | `test_rejects_caller_defined_scalar_subclasses` |
| Canonical evidence cannot be forged after construction | `test_revalidates_live_state_before_serialization`, `test_revalidates_recorded_time_before_digesting` |
| A request never grants execution authority | `test_request_is_explicitly_non_authorizing_and_value_minimized` and closed action regressions |
| Application disposition does not claim media sanitization | `media_sanitization_state == "not_claimed"` regression in `test_request_is_explicitly_non_authorizing_and_value_minimized` |
| Owned production statement/branch coverage | `HR Data Disposition Quality` exact-head workflow with `--cov-branch --cov-fail-under=100` |

## Dependency and ownership

PR #76 is the dependency root for this slice and must integrate first. Descendant checks are never transferred as protected-base evidence. After the parent integrates, this PR must be retargeted to a fresh protected `develop` tip and rerun on its new exact head.

The request binds only Orgmetra-owned opaque evidence. It does not mutate Keyverse, Naruon, MHTML ETL Gateway, mightyETL, or any other dedicated-writer repository and does not use cross-service application-table SQL.
