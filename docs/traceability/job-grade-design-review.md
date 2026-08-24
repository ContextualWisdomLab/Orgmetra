# Job grade design review traceability

Status: **active PR truth only**. Protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has authoritative Job and persisted Job Analysis snapshot foundations but does not yet contain this review packet or authoritative Job-grade persistence.

| Buyer / governance requirement | Active-PR implementation | Evidence / verification |
|---|---|---|
| Bind a grade proposal to authoritative Job scope | `tenant_record_id` + `job_record_reference` | Canonical operational UUID validation; tenant/Job scope regression |
| Bind exact Job-analysis evidence | snapshot reference + `job_analysis_snapshot_digest` | Canonical reference and lower-case SHA-256 regressions |
| Preserve evaluation-method provenance | `job_evaluation_method_code` + method digest | Bounded lower snake_case code and exact SHA-256 validation |
| Keep grade and band normalized but enterprise-local | separate `grade_code`, `band_code`, architecture digest | Uppercase token validation; no universal rank/pay semantics |
| Require accountable human review | distinct requester/reviewer UUIDv4 actor correlations | Actor-separation and UUIDv4 regressions |
| Version the durable review contract | fixed canonical `evidence_version = 1` | Exact built-in integer validation; omitted/unsupported/coercible versions cannot create a different schema claim |
| Separate human review from system recording | exact UTC `reviewed_at` and `recorded_at` | `recorded_at >= reviewed_at`; hostile/non-UTC datetime rejection |
| Minimize durable evidence | hashes/correlations/codes only | Canonical JSON privacy regression excludes Job text, Person/candidate/worker PII, pay, ratings, free text, prompts/model output and credentials |
| Prevent evidence from becoming decision authority | fixed purpose/state/authority/human-review/next-action fields | Direct-construction weakening regressions |
| Detect post-issuance in-process mutation | process-local weak issuance digest registry | `object.__setattr__` tamper regressions fail canonical document/JSON/digest export |
| Preserve standalone / MSA extraction boundary | package contains no cross-service SQL or foreign writes | Source/package review; foreign methods are research inputs only |
| Exact owned coverage | dedicated exact-head workflow | `Job Grade Design Quality` requires 100% statement + branch coverage and clean checkout |

## State boundaries

- **Protected-main truth:** authoritative Job identity, bitemporal HRIS foundations, persisted governed Job Analysis snapshot, audit/outbox foundations.
- **Active PR truth (#101):** governed non-authoritative Job grade/band design review packet and its exact-head quality gate.
- **Active stacked descendant (#109):** proposed normalized bitemporal Job-grade persistence consuming this exact versioned canonical packet; it remains Draft and is not protected-main truth.
- **Planned after integration:** purpose-bound API/UI access and accessible Storybooked/Figma product interaction when material.
- **Research-only:** ILO gender-neutral Job evaluation guidance and OPM Factor Evaluation System are methodological inputs. OPM federal classification rules are not an Orgmetra enterprise standard.
- **Out of scope:** compensation amount/ranges, payroll, statutory accounting, automatic employment decisions, direct mutation of foreign CWL repositories.

## Next authoritative action

Before any reviewed proposal is persisted as HRIS truth, re-read the exact tenant Job, persisted Job Analysis snapshot, evaluation-method definition, and enterprise grade/band architecture; verify all digests, `evidence_version`, and reviewer authority; then write one bitemporal Job-grade fact and immutable audit/outbox evidence in a single Orgmetra-owned transaction. Do not infer compensation or an employment outcome from the review packet.
