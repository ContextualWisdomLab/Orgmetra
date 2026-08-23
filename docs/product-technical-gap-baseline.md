# Product and technical gap baseline

Inventory date: 2026-08-23 (Asia/Seoul). Protected `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

Orgmetra owns employment truth (`organization_unit`, `assignment_record`, `person_record` bound to a Keyverse subject). IdP/SCIM issuance is Keyverse. Orgmetra pins `X-CWL-Tenant-Reference` to `tenant_record` and does not issue the header. Journal truth is AIS. Commercial collection is Billing. Measurement and delivery are Psychometrics.

Next operator action: do not self-approve as `seonghobae`. Merge a Ready PR only when a non-author OpenCode APPROVE sits on that exact SHA and product/security checks on that SHA are terminal green. Treat 5-6s OpenCode/Noema jobs as stubs, not receipts.

## What is already on protected develop

| Merged PR | Capability |
|---|---|
| #26 | `validity_study_case_record` integrity (migration 0010) |
| #28 | Performance-criterion job-scope guard (migration 0011) |
| #31 | Governed People mutation API |
| #38 | Governed job-analysis snapshot persist/read |

Do not revive those heads.

## Open PRs included in this baseline

All listed PRs are authored by `seonghobae`. Independent OpenCode APPROVE was not present on sampled Ready heads at inventory time.

### Draft

| PR | Head SHA | Branch | Intent |
|---|---|---|---|
| [#99](https://github.com/ContextualWisdomLab/Orgmetra/pull/99) | `09dc3135606669cdd60778db531cd3f6af34e171` | `feat/employment-compensation-core` | Employment-scoped bitemporal base compensation |
| [#82](https://github.com/ContextualWisdomLab/Orgmetra/pull/82) | `0c3a776f2e2c6f93c25e11c5c3ce3fa66a10b5c9` | `feat/outbox-retry-policy` | Outbox retry (base is not develop) |
| [#77](https://github.com/ContextualWisdomLab/Orgmetra/pull/77) | `9b02cb911377a5beb9f541e9acf2eb51ff065ee9` | `feat/hr-data-disposition-request` | HR data disposition (stacked on #76) |

Keep Draft until product, Strix, CodeQL, and Semgrep are green on the exact SHA.

### Ready on develop (factory queue)

| Order | PR | Head SHA | Title |
|---:|---|---|---|
| 1 | [#97](https://github.com/ContextualWisdomLab/Orgmetra/pull/97) | `9715b06d0a459aed7f29293e02de8c2a452e2b87` | Bitemporal Position vacancy evidence |
| 2 | [#98](https://github.com/ContextualWisdomLab/Orgmetra/pull/98) | `9aeeb204acce429f85b028029c9531a5b05f37e1` | Governed HR document evidence |
| 3 | [#80](https://github.com/ContextualWisdomLab/Orgmetra/pull/80) | `2300c0a0605d89e58aa70ac04b0dee9a7d516882` | Candidate offer response evidence |
| 4 | [#81](https://github.com/ContextualWisdomLab/Orgmetra/pull/81) | `78a9cb1e047db5c79ca855b992d44749b9214992` | contextual-orchestrator draft evidence |
| 5 | [#94](https://github.com/ContextualWisdomLab/Orgmetra/pull/94) | `3f67182bb3065f2fc8fd974bfdd75a390d8a8fdc` | Bitemporal position reporting hierarchy |
| 6 | [#95](https://github.com/ContextualWisdomLab/Orgmetra/pull/95) | `adf055d79d188ba18d06ecf80dc1117858c987f4` | Position reporting-change review |
| 7 | [#96](https://github.com/ContextualWisdomLab/Orgmetra/pull/96) | `b9f8e3d291c4bdcd2f0aa5f9d0378dea09e5e7cd` | Organization hierarchy-change review |
| 8 | [#45](https://github.com/ContextualWisdomLab/Orgmetra/pull/45) | `e0af2501d540de48f7c0e0e3d09ac3e2e5417d2b` | Assignment change review packet |
| 9 | [#46](https://github.com/ContextualWisdomLab/Orgmetra/pull/46) | `595c190e30e499abea1284c7307ea0783ada1efd` | Employment separation review packet |
| 10 | [#44](https://github.com/ContextualWisdomLab/Orgmetra/pull/44) | `482d2970cf872cb6f0b4e15fb8805f8bbfd990ff` | Performance review packet |
| 11 | [#42](https://github.com/ContextualWisdomLab/Orgmetra/pull/42) | `9b871a3245671f0d14ea56e103ac0d9b91482d43` | Selection outcome monitoring plan |

Also open on develop (re-verify head before acting): #93, #92, #91, #90, #53, #88, #87, #83, #86, #84, #85, #79, #78, #76, #75, #74, #73, #65, #56, #48, #47, #54.

Sampled reviews: #97 and #98 have Devin COMMENT only. Combined status on #97 `9715b06` was success (CodeRabbit rate-limited). That is not an OpenCode receipt.

## Buyer-facing gaps after the open queue

Do not open withholding, payroll-pay, or year-end settlement tables or UI.

1. Job-grade design screen against a persisted job-analysis snapshot (`job_grade_structure`, `job_grade_band`, Storybooked).
2. Job-analysis LLM draft assist via contextual-orchestrator and NVIDIA NIM. Human confirm before snapshot persist.
3. Offer-to-hire close: #80 response plus #31 mutation as one operator path.
4. Vacancy-to-assignment: #97 seat can be opened, filled, or frozen against `assignment_record`.
5. Purpose-bound document retrieve/export for #98 (audit, no PII masking).
6. Storybook, design tokens, and a Figma file id in an ADR for any new screen.
7. Ecosystem only: consume Keyverse subject; emit assignment keys to Psychometrics; emit compensation proposals to AIS after a portal role code exists. Do not own statutory accounts.

## Technical non-negotiables

- 100% docstring and coverage on new modules; realistic cases (round-trip persist, not status 200 only).
- Database objects: two-or-more-word snake_case, 3NF, tenant plus recorded-time keys against hot partitions.
- Purpose-bound authorization, encryption, retention, audit.
- CSAP and SOC 2 on every write path.
- Modular MSA. Split the repo if it becomes a monolith.
- Failed Checks: fix on the failing SHA. Review wait is not a stop.

## Loop

Hourly: inventory open PRs, review, fix real defects, re-verify exact-head checks, merge only with non-author OpenCode APPROVE, then the next gap from this file. Refresh this document when a listed SHA moves or a PR merges.

## Doctoring (APA 7th)

Equal Employment Opportunity Commission. (1978). Uniform guidelines on employee selection procedures (29 C.F.R. Part 1607).
Society for Industrial and Organizational Psychology. (2018). Principles for the validation and use of personnel selection procedures (5th ed.).
International Organization for Standardization. (2018). ISO 30414: Human resource management — Guidelines for internal and external human capital reporting.
American Educational Research Association, American Psychological Association, and National Council on Measurement in Education. (2014). Standards for educational and psychological testing.
