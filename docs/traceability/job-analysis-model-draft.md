# Job Analysis model-draft traceability

This traceability file describes **active PR truth only** until the owning branch is integrated into `develop`.

| Requirement / risk | Owner boundary | Executable evidence |
|---|---|---|
| Model work must not start before exact tenant/Job Analysis snapshot/purpose/requester authorization, and the exact authority evidence must remain correlated | `generate_job_analysis_model_draft` + injected `scope_resolver` | `test_authority_rejection_prevents_model_and_human_work`; `test_scope_verification_must_match_exact_request`; happy-path receipt assertion |
| Drafting evidence must cover Task, FJA, and KSAO rather than an incomplete evidence family | `JobAnalysisDraftRequest.semantic_units` | `test_request_requires_task_fja_and_ksao_semantic_units` |
| Runtime semantic text must be content-digest bound, source-provenance bound, sorted, and unique | `SemanticUnit`; `JobAnalysisDraftRequest` | `test_semantic_units_are_digest_bound_and_canonically_ordered` |
| Raw Task/FJA/KSAO text must not enter durable evidence | `SemanticUnit.evidence`; request canonical document | `test_happy_path_binds_semantic_units_and_human_review_without_authorizing_persistence` |
| Model output is untrusted and must be digest/provenance/revision/route bound | `DraftModelResult` | `test_model_result_is_digest_bound_and_revision_pinned` |
| Contextual Orchestrator remains an injected read-only dependency boundary | workflow `orchestrator` callable | happy-path ordering and exact callback-result-type regressions; no foreign repository/application-table import exists in this package |
| Human reviewer must be distinct and use a controlled confirmation/rejection reason, and that reason must survive in durable evidence | `HumanDraftReview`; workflow actor-separation and receipt construction | `test_human_reviewer_must_be_distinct_and_reason_compatible`; `test_rejected_draft_is_auditable_but_never_persistence_authority`; `test_rejected_draft_preserves_controlled_human_reason_in_durable_evidence` |
| A rejected human review must not direct the next actor toward authoritative persistence | receipt `review_state` / `next_action` mapping | `test_rejected_draft_preserves_controlled_human_reason_in_durable_evidence` requires `revise draft evidence before authoritative submission` for rejected evidence |
| Human confirmation cannot become Job Analysis persistence authority | `JobAnalysisModelDraftReceipt` canonical evidence | happy-path/rejected-draft regressions assert `not_authorized_for_job_analysis_persistence` |
| Checked request/model evidence cannot be rewritten during injected callbacks | workflow request/model snapshots | authority/model/human mutation regressions |
| Runtime draft bytes cannot be detached from the reviewed receipt digest after issuance | `JobAnalysisModelDraftOutcome` construction/read check | `test_runtime_outcome_cannot_detach_draft_text_from_receipt` |
| Caller-defined runtime subtypes, malformed IDs/digests/timestamps, and invalid callback result types fail closed | validators + exact-type callback boundaries | malformed-governance, timestamp, semantic collection, scope-verification, and callback-result regressions |
| Issued durable evidence must detect post-issuance rewriting | process-local receipt seal + workflow-only issuance token | `test_receipt_rejects_direct_replacement_and_post_issuance_mutation` |
| Public Python support must not silently widen beyond the hosted minor | package metadata + exact CI runtime | `test_python_support_is_bounded_to_the_exact_hosted_minor` requires `>=3.14,<3.15` and exact CPython 3.14.7 |
| Installed package evidence must be reproducible and hash-bound | package-specific reviewed build-backend lock + exact-checkout local wheel | `test_isolated_install_hash_binds_backend_and_exact_local_wheel` requires SHA-256-locked setuptools, local wheel construction, computed wheel digest, and `pip --require-hashes` installation |
| Owned production code remains exactly 100% statement/branch covered | package pytest/coverage policy | `Job Analysis Model Draft Quality` exact-head workflow |

## Boundary to authoritative persistence

A `human_confirmed_draft` receipt is evidence that a human reviewed a specific digest-bound model draft under a specific authorized Job Analysis snapshot, including a controlled reason code for that human review. It is **not** evidence that the current authoritative Job Analysis still matches that snapshot and is not authorization to persist. A rejected draft instead carries a revision-only next action and must not be submitted as if human-confirmed. The authoritative Job Analysis persistence boundary must re-resolve current tenant/snapshot/actor scope, inspect the receipt/evidence version, apply its own human decision policy, and append immutable audit/outbox evidence before authoritative mutation.

## Protected-main versus active-PR truth

Protected-main at proposal time does not contain this package. This document must not be cited as proof that model-assisted drafting is shipped until the owner PR is integrated and fresh default-branch evidence confirms the capability.
