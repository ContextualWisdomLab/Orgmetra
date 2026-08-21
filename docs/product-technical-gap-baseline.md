# Orgmetra product and technical gap baseline

**Snapshot:** 2026-08-21, Asia/Seoul
**Evidence base:** protected `develop` at `33eff439df5c2ef58805c975108d156fd73799df`; current workspace PR #53 at `a9442e2375694894c084d08768046e9d6c8d7cb9`; current GitHub PR metadata and exact-head workflow state observed on 2026-08-21.

This document is the buyer-facing work queue. It separates what a customer can use from what exists only in an active PR or architecture document. It is updated when a protected merge, exact-head check, review, release, or runtime test changes the evidence boundary.

## Maturity vocabulary

| Value | Meaning |
|---|---|
| `implemented_on_protected_develop` | Executable behavior and its required evidence are on the protected default branch. |
| `implemented_on_active_pr` | Code or tests exist on a current PR, but protected-branch runtime truth is not established. |
| `accepted_architecture` | An owned boundary and contract are accepted, but the buyer workflow is not executable here. |
| `planned` | Product work is named and ordered, but implementation evidence is missing. |
| `research_only` | A paper, prototype, or external product informs a decision; it is not an Orgmetra capability. |
| `superseded` | The artifact must not be revived because a newer owner or contract replaced it. |
| `out_of_scope` | The capability belongs to another product or is intentionally not an Orgmetra decision. |

## Executive finding

Orgmetra is an evidence-centered HRIS foundation with protected Job Analysis, candidate-evidence, People mutation, and confirmed-hire boundaries, not yet a complete commercial HCM product. The protected branch provides durable PostgreSQL integrity contracts, a Python HRIS decision kernel, purpose-bound authorization, governed candidate-to-worker lineage, and executable Job Analysis and People read/write boundaries. The largest buyer-visible gap remains the missing connected browser product surface: the current checkout has an active-PR HR Home/Employee Profile fixture and local Storybook state runtime, but protected truth has no connected or released workspace.

The next highest-leverage gaps are a connected/released buyer path over the now-protected Job Analysis API and actual statistical validity estimation. Existing contracts are useful foundations, but they do not substitute for a running customer path or a released deployment.

```mermaid
flowchart LR
    evidence[Job and candidate evidence] --> selection[Human selection record]
    selection --> mutation[People mutation boundary]
    mutation --> worker[Employment, position, assignment]
    worker --> outcome[Performance outcomes]
    outcome --> validity[Validity estimation]
    validity --> policy[Human-reviewed policy change]
    worker -. browser workspace missing .-> gap1[Gap P0-1]
    worker -. buyer-connected Job Analysis path missing .-> gap2[Gap P0-2]
    validity -. integrity only, no estimator .-> gap3[Gap P0-3]
```

## Capability truth on protected `develop`

| Capability | Current evidence | Maturity | Buyer consequence |
|---|---|---|---|
| Person, employment, organization, job, position, assignment separation | `database/migrations/0001_foundation_schema.sql`; HRIS kernel tests; bitemporal and tenant contracts | `implemented_on_protected_develop` | Employment truth can be modeled without collapsing stable identities or historical versions. |
| Tenant isolation, append-only history, evidence sealing, audit/outbox integrity | Migrations `0001`–`0012`; PostgreSQL contract suite; `npm run validate` | `implemented_on_protected_develop` | The foundation can reject cross-tenant, temporal, evidence-drift, and unsafe delivery-state writes. |
| Candidate evidence intake | Protected candidate-evidence package, ADR `0025`, reference-only packet tests, and `Candidate Evidence Quality` workflow | `implemented_on_protected_develop` | Candidate evidence can be correlated without copying raw values or PII into the governance envelope; authoritative reference resolution and selection remain separate boundaries. |
| Candidate-to-worker conversion | Migration `0009`; `test_candidate_worker_conversion_postgres.sh`; protected traceability; People API hire route | `implemented_on_protected_develop` | Confirmed-hire materialization has a governed HTTP/service boundary; deployment and browser evidence remain separate release work. |
| People read | `services/people-api` GET route, PostgreSQL read adapter, HTTP tests | `implemented_on_protected_develop` | Authorized HR users can read a worker view; responses are no-store and field-scoped. |
| People mutations | Migration `0012`; `services/people-api` hire and mutation routes; current protected service tests and PostgreSQL contract | `implemented_on_protected_develop` | Authoritative person, employment, position, assignment, and confirmed-hire writes have a governed code boundary; hosted/browser release evidence remains open. |
| Job-analysis value objects | `orgmetra_hris_kernel.job_analysis`; exact unit coverage | `implemented_on_protected_develop` | Evidence can be validated in a protected package and reused by the persisted Job Analysis boundary; buyer workflow connectivity remains open. |
| Job-analysis persistence/API | Protected migration `0013`, `services/job-analysis-api`, ADR `0014`, PostgreSQL contract, and exact snapshot tests on `develop` | `implemented_on_protected_develop` | A buyer-facing deployment and browser workflow are still absent, but one canonical persisted Job Analysis case/API now exists in protected code. |
| Performance criterion scope and validity-study case integrity | Migration `0010`/`0011`; PostgreSQL contracts | `implemented_on_protected_develop` | Invalid worker-Job/time links are rejected, but no statistical validity estimate is produced. |
| Statistical validity estimation | Traceability explicitly says estimation is subsequent; no Rust workspace or estimator exists in this repository | `planned` | Customers cannot measure prediction, bias, RMSE/MAE, uncertainty, convergence, temporal effects, or multiple membership. |
| Workforce composition change evidence | Active PR #54 adds same-cutoff bitemporal composition-change evidence | `implemented_on_active_pr` | Buyers can review a proposed workforce change only after the exact PR earns checks and independent approval; it is not protected truth yet. |
| Organization hierarchy snapshot evidence | Active PR #56 adds bitemporal organization hierarchy snapshot evidence | `implemented_on_active_pr` | Organizational reporting remains an active integration lane, not a protected or released buyer workflow. |
| Selection-validity analysis handoff | Active PR #57 adds the governed handoff boundary for later validity estimation | `implemented_on_active_pr` | The handoff is not a statistical estimator and does not yet produce validity, bias, RMSE, coverage, or convergence evidence. |
| Role workspaces and Storybook runtime | Active PR #53 has the HR Home/Employee Profile fixture plus a local Storybook `10.5.10` build; protected `develop` still has no customer UI | `implemented_on_active_pr` | The local component/state runtime is reviewable, but there is no connected or released buyer workflow in protected truth. |
| Naruon calendar adapter | `packages/naruon-adapter` package tests; traceability says planned integration | `accepted_architecture` | Calendar intent is contract-tested, not an integrated customer scheduling workflow. |
| TEPP adapter | PR #52 is a non-executing request boundary; no transport contract is established | `implemented_on_active_pr` | Temporal analysis can be prepared as governed evidence but is not executed by Orgmetra. |
| Contextual Orchestrator/OpenCode model path | Named in architecture; no Orgmetra adapter or evidence-backed model evaluation in protected code | `planned` | LLM assistance cannot yet be invoked through an Orgmetra-owned, auditable draft-evidence boundary. |
| Search, semantic chunking, and image understanding | Architecture mentions derived search/vector storage, but no owned schema, chunker, OCR/object metadata, or index adapter is present | `planned` | Evidence retrieval cannot yet preserve paragraph/DOM/image location semantics for customer search. |
| Hot-partition scale strategy | No `PARTITION BY`/partition-management contract in the current migrations | `planned` | Append-heavy audit/outbox and temporal tables need a tested scale plan before high-volume production. |
| CSAP/SOC 2 evidence package | Security, threat, operability, and test documents exist; no control-evidence collection or attestation exists | `accepted_architecture` | The design is compliance-ready in intent, not a certification or audit report. |
| Release artifact | Root package is `0.1.0`; changelog remains `[Unreleased]`; no protected product release was verified | `planned` | Customers have no versioned, supportable Orgmetra product release yet. |

## Local candidate artifact outside protected truth

The current checkout contains `apps/hr-workspace/`, a dependency-free HR Home
and Employee Profile fixture based on Figma nodes `1:10` and `1:28`. It uses
the shared design tokens and proves navigation, focus-visible styling,
keyboard-accessible evidence and confirmation dialogs, purpose-bound
permission denial, exact allocation values, and English/Korean labels. The
fixture explicitly displays that the protected People API is not connected.
The same active PR includes a local Storybook runtime with tokenized stories;
the current head has a passed Storybook build and local Playwright browser
smoke, but neither is connected People API integration, hosted deployment, or
protected-develop truth. The artifact must be reviewed, checked, and merged
independently before P0-1 can change maturity.

## Buyer gap backlog

| ID | Priority and owner | Gap and smallest acceptable closure evidence | Dependency |
|---|---|---|---|
| P0-1 | Product / Web | Review and merge the active HR Home + Employee Profile fixture and local Storybook states, then connect it to the protected People API and prove keyboard/focus/permission/confirmation states, exact-value tables, i18n, and browser E2E. | Protected People API evidence |
| P0-2 | Job Architecture | Protected `develop` now contains PR #38's persisted Job Analysis case/API, migration owner, ADR, versioned source evidence, and PostgreSQL acceptance tests. Connect it to the buyer workflow, SME approval path, deployment, and browser evidence. | Protected People API evidence; active workspace path |
| P0-3 | Workforce Validation / scientific owner | Advance active PR #57 into a Rust-first estimator boundary or versioned adapter to `fast-mlsirm`/TEPP. Publish true-parameter recovery, bias, MAE, RMSE, coverage, convergence, temporal, multilevel, multiple-membership, CPU reference, and material GPU parity evidence. | Protected P0-2 and external contract re-resolution |
| P0-4 | Release / Platform | Produce a deployable release with version, changelog, migration inventory, rollback/recovery evidence, support runbook, and exact commit provenance. | P0-1 through P0-3 |
| P1-1 | Integration Hub | Implement contextual-orchestrator adapter for draft evidence only. Pin model/provider/config/evidence digests, use `NVIDIA_NIM_API_KEY` for model-backed development, and record ablations for single-route versus multi-agent depth/access lists. | P0-2; external runtime contract |
| P1-2 | Evidence Platform | Add normalized document/image segment metadata: semantic unit, source location, OCR/object tags, image reference, sensitivity, retention, embedding model/version, and owner provenance. Query filters must run before similarity ranking. | P0-2; document owner contracts |
| P1-3 | Data Platform | Define and rehearse hot-partition strategy for append-heavy audit/outbox and temporal facts, including tenant/time key choice, partition creation, retention, reindexing, and cross-partition query tests. | P0-1; production volume evidence |
| P1-4 | Trust / Operability | Build a CSAP/SOC 2 control matrix with owner, control activity, evidence location, retention, incident path, and release approval. Label it readiness evidence, never certification. | P0-1/P0-2 |

## Current open PR inventory and integration order

The following is the current GitHub inventory checked on 2026-08-21. All listed PRs target `develop@33eff439df5c2ef58805c975108d156fd73799df`. `REVIEW_REQUIRED` means the GitHub listing reported that review gate; it is not approval evidence. No self-approval or protection bypass is permitted.

| PR | Head branch / exact head | Scope | Current state | Next action |
|---:|---|---|---|---|
| 57 | `feat/validation-analysis-handoff` / `f0c30c5e6cfd6cb90afcbef1efd0ba8825f3fd52` | Governed selection-validity analysis handoff | Draft; mergeable; base `33eff43`; `REVIEW_REQUIRED`; current workflow runs queued/pending | Review the handoff boundary and keep estimator claims separate until exact-head checks and independent approval exist. |
| 56 | `feat/organization-hierarchy-snapshot` / `95e6ce7f5d4a07322129635b2adfd0f890b61d2b` | Bitemporal organization hierarchy snapshot evidence | Draft; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify tenant/time semantics and current-head checks before independent approval. |
| 55 | `fix/people-read-auth-backend-failure` / `a650d5b8040f3c8a0a11b516b99c814d89508d57` | People-read error normalization and pre-auth resource budgets | Draft; mergeable; base `33eff43`; `REVIEW_REQUIRED`; current workflows queued | Reproduce any review finding on this exact head, then wait for terminal People API/security/recovery checks and independent approval. |
| 54 | `feat/workforce-composition-change` / `db4ea77221e0318dc2ab1be26543e338683d7678` | Same-cutoff workforce composition change evidence | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED`; current workflows queued | Re-fetch exact head, terminal checks, resolved threads, and qualifying independent approval before merge. |
| 53 | `codex/product-gap-baseline-workspace` / `a9442e2375694894c084d08768046e9d6c8d7cb9` | HR Home + Employee Profile fixture, Storybook, and baseline repair | Draft; mergeable; base `33eff43`; `REVIEW_REQUIRED`; current workflows queued/pending | Keep the fixture/API boundary explicit, wait for all current-head checks, obtain independent approval, then decide whether to merge the product-surface slice. |
| 52 | `feat/tepp-analysis-adapter` / `fcbd800513c3605b78347daa283ec58291f0bc28` | Governed TEPP analysis request boundary | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Keep non-executing and evidence-bound; merge only after exact-head checks and qualifying review. |
| 51 | `docs/protected-truth-refresh` / `fa3b6e9c9cd449f577cf0b493aad561fb7376327` | Protected product-truth documentation repair | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Reconcile documentation with protected runtime truth, then use current-head checks and independent review. |
| 48 | `feat/governed-compensation-change-review` / `f6cefeb64d214e020ed82840b64d7d0cca70ec6e` | Compensation review packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify high-impact confirmation/evidence boundaries, then merge only with terminal checks and independent approval. |
| 47 | `feat/governed-employment-leave-review` / `088abb13c1f1b2aa69c6e68b1814ce13fb08e4d9` | Employment leave review packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify temporal and authorization contracts before protected merge. |
| 46 | `feat/governed-employment-separation-review` / `add78f169a01d72ad2e027a3fae9f83ce795721f` | Employment separation review packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify irreversible-action confirmation and audit evidence before protected merge. |
| 45 | `feat/governed-assignment-change-review` / `18ac3a733f775b67dbe0260b5b59699bc0d10301` | Assignment change review packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify tenant/person/employment/position binding before protected merge. |
| 44 | `feat/governed-performance-review` / `b867f4cf1efdec198f34199e7e8c382338e94505` | Performance review packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify criterion scope and human confirmation before protected merge. |
| 43 | `feat/governed-offer-approval` / `8af2e3bf31bb9352033bded6530b9357405782af` | Offer approval packet | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify evidence-backed offer approval and audit/outbox behavior before protected merge. |
| 42 | `feat/selection-outcome-monitoring-plan` / `a306d8199be475ba07682e31c1f9b4d9c701a50b` | Selection outcome monitoring | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify monitoring scope and temporal cohort semantics before protected merge. |
| 40 | `feat/structured-interview-plan` / `6e6cc4f6b9c1356773cb3d89a52bcbf4bdfcadba` | Governed structured interview plan | Ready; mergeable; base `33eff43`; `REVIEW_REQUIRED` | Verify human review, evidence versioning, and current-head checks before protected merge. |

No open GitHub Issue was returned by the current `gh issue list` query. This does not mean product work is exhausted: the backlog above is derived from protected runtime gaps and is intentionally independent of issue presence.

## Operating scheduler boundary

The review/repair/merge sweep is centrally owned by
[`ContextualWisdomLab/.github`](https://github.com/ContextualWisdomLab/.github/blob/main/.github/workflows/pr-review-merge-scheduler.yml), not copied into Orgmetra. The live central `main` workflow currently exposes `*/15` and `*/30` GitHub Actions sweeps, which is more frequent than the hourly operating contract below. Its organization sweep dispatches target-repository scans while target checks still execute against the target repository's exact head. Orgmetra therefore has no repository-local privileged scheduler or model credential path; this is an accepted control-plane boundary, not evidence that any individual PR is merge-ready.

## Loop contract

Every central scheduler sweep performs the same bounded sequence:

1. Re-fetch the protected `develop` head and current open PR list.
2. For each open PR, inspect current review threads, exact head, mergeability, and all repository/security/recovery/coverage checks.
3. If a review comment identifies a defect, reproduce it on the exact head, make the smallest root-cause repair, and re-run the full affected suite.
4. Never transfer checks or approvals from a predecessor head. Never self-approve, bypass protection, cancel a pending gate to create a result, or call an unmerged PR shipped.
5. Merge only when the current head, current base, required checks, resolved threads, and independent approval satisfy live repository rules. Record the merge SHA and continue to the next dependency-ready lane.
6. If no PR is merge-ready, advance the highest-priority unblocked product gap and leave a verifiable branch/PR artifact.
7. Re-run `npm run validate`, the affected `uv` package suite, PostgreSQL contracts, and browser evidence before release claims.

The loop is an operating procedure, not evidence of completion. Its next customer action must always be explicit: approve, review, correct, request evidence, compare, export, or escalate.

## Standards and research alignment

- ISO 30405:2023 grounds the recruitment lifecycle and the requirement to connect preparation, assessment, stakeholders, review, and learning.
- EEOC Uniform Guidelines and SIOP validity guidance ground job-related selection evidence and prohibit treating a statistical link as sufficient without job scope, criterion integrity, and human governance.
- NIST AI RMF 1.0 requires continuous governance, mapping, measurement, and management of AI risks; Orgmetra therefore keeps LLM output as draft evidence and requires human authority.
- AICPA Trust Services Criteria provide the SOC 2 readiness vocabulary for security, availability, processing integrity, confidentiality, and privacy; Orgmetra has readiness documentation but no attestation claim.
- WCAG 2.2 is the target UI baseline. The existing Figma file and design tokens are inputs; the missing evidence is executable accessibility and interaction testing.
- Fugu, Conductor, and TRINITY support evaluating when a single route is enough and when role-specialized multi-agent depth, recursion, and access lists improve evidence work. Orgmetra must measure this through contextual-orchestrator artifacts rather than assuming multi-agent quality.

The complete APA 7 bibliography is in `docs/doctoring/REFERENCES.md`.

## Fresh local evidence

| Check | Result |
|---|---|
| Protected `develop` contents | `git ls-tree` at `33eff439df5c2ef58805c975108d156fd73799df` contains migration `0013`, Job Analysis API, ADR `0014`, candidate-evidence package, ADR `0025`, and their quality workflows. This proves repository presence, not deployment. |
| `npm run validate` on active PR #53 | Passed: foundation validation and 60 Node tests on exact local head `eedcf1c34bd6dc6e94fc0c70802c6f7d43090034`. |
| `packages/candidate-evidence` on active PR #53 | 75 passed; owned statement and branch coverage 100%. |
| Storybook and browser fixture | Storybook `10.5.10` production build passed; Playwright browser smoke passed for four action states, exact allocation values, locale switching, localized accessible names, and zero console/page errors. This is local fixture evidence, not protected deployment or People API integration. |
| PostgreSQL and full Python package matrix | Protected-branch contract evidence remains recorded in the merged package/workflow artifacts; a complete fresh matrix was not rerun in this documentation-only update and must be required by the corresponding hosted workflows. |

These results prove the current foundation contracts. They do not prove that open PRs are merged, that a browser UI exists, that a statistical estimator exists, or that Orgmetra is certified under CSAP/SOC 2.
