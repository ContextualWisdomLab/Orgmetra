# Performance Goal Activation Traceability

Status: **active stacked PR #121; not protected-main truth**.

| Requirement | Owner boundary | Executable evidence |
| --- | --- | --- |
| Only exact reviewed goal-plan objects may activate | `activate_performance_goal_plan` | `test_activation_rejects_non_plan_before_authority_work` |
| The approving human must be the reviewer bound by the reviewed packet | activation orchestration | `test_activation_requires_the_reviewed_human_actor` |
| Approval cannot predate reviewed evidence and timestamps use exact built-in fixed offsets | activation orchestration / verification | `test_activation_rejects_untrusted_approval_timestamp_runtime`, `test_activation_rejects_approval_before_review_evidence_exists`, `test_verification_rejects_untrusted_timestamp_runtime` |
| Tenant, Employment, Job, cycle, goal provenance, measurement provenance, cadence, actor and approval instant are freshly rebound by the host authority | `PerformanceGoalPlanActivationAuthority` + exact verification snapshot | `test_activation_rejects_authority_scope_drift` |
| Authority cannot rewrite the reviewed packet during verification | parent creation seal recheck after authority call | `test_activation_rejects_plan_mutation_across_authority_call` |
| Duck-typed authority output cannot masquerade as governed verification | exact verification runtime type | `test_activation_rejects_non_verification_authority_result` |
| Verification evidence is value-minimized, chronologically coherent and fixed to non-decision authority | `PerformanceGoalPlanActivationVerification` | `test_verification_rejects_invalid_chronology_and_governance`, `test_verification_requires_exact_evidence_version_one` |
| Receipt emission preserves value minimization and does not grant rating/employment-decision authority | `PerformanceGoalPlanActivationReceipt` | `test_activation_emits_value_minimized_authority_bound_receipt` |
| Direct construction, replacement, copying or low-level rewriting cannot create a second valid activation truth | factory issuance token + process-local creation seal | `test_receipt_cannot_be_constructed_or_rewritten_outside_activation`, `test_copied_receipt_has_no_issuance_seal`, `test_receipt_rejects_impossible_activation_chronology_before_token_check`, `test_receipt_requires_exact_evidence_version_one` |
| Installed package code, not source-tree-only imports, satisfies exact 100% owned statement/branch coverage | dedicated workflow | `.github/workflows/performance-goal-activation-quality.yml` |

## Boundary truth

PR #92 owns the reviewed plan packet. PR #121 owns only authoritative activation orchestration and activation receipt evidence. It does **not** own durable activation persistence, performance ratings, compensation, promotion, discipline, separation, or another employment decision. Those remain separate authoritative workflows with their own human-review and immutable-audit obligations.

This child is dependency-first under #92. Stack-local GREEN, if obtained, does not transfer parent checks or reviews and does not authorize merge. After #92 integrates, #121 must be retargeted to the fresh `develop` head and all applicable current-head local and central gates rerun.
