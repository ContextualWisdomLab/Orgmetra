# Orgmetra product and technical gap baseline

**Snapshot:** 2026-08-21, Asia/Seoul
**Evidence base:** protected `develop` at `9e3e4847510e1e612b48474ba42b177b8ed824df`; current workspace PR #53 at `88f809b030bb4ea2568810f1fd68bdc27d74c230` immediately before this documentation snapshot commit; current GitHub PR metadata and exact-head workflow state observed on 2026-08-21.

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

Orgmetra is an evidence-centered HRIS foundation with protected Job Analysis, candidate-evidence, People mutation, and confirmed-hire boundaries, not yet a complete commercial HCM product. The protected branch provides durable PostgreSQL integrity contracts, a Python HRIS decision kernel, purpose-bound authorization, governed candidate-to-worker lineage, and executable Job Analysis and People read/write boundaries. The largest buyer-visible gap remains the missing connected browser product surface: the current checkout has an active-PR HR Home/Employee Profile fixture plus an API-bound Job Analysis read surface and local Storybook state runtime, but protected truth has no connected or released workspace.

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
| Offer approval packet | Protected `packages/offer-approval` packet, actor-separation/evidence-version tests, and `Offer Approval Quality` workflow | `implemented_on_protected_develop` | Offer approval evidence is bounded and human-reviewed; a connected buyer workflow and released deployment remain open. |
| Job-analysis value objects | `orgmetra_hris_kernel.job_analysis`; exact unit coverage | `implemented_on_protected_develop` | Evidence can be validated in a protected package and reused by the persisted Job Analysis boundary; buyer workflow connectivity remains open. |
| Job-analysis persistence/API | Protected migration `0013`, `services/job-analysis-api`, ADR `0014`, PostgreSQL contract, and exact snapshot tests on `develop` | `implemented_on_protected_develop` | A buyer-facing deployment and browser workflow are still absent, but one canonical persisted Job Analysis case/API now exists in protected code. |
| Performance criterion scope and validity-study case integrity | Migration `0010`/`0011`; PostgreSQL contracts | `implemented_on_protected_develop` | Invalid worker-Job/time links are rejected, but no statistical validity estimate is produced. |
| Statistical validity estimation | Traceability explicitly says estimation is subsequent; no Rust workspace or estimator exists in this repository | `planned` | Customers cannot measure prediction, bias, RMSE/MAE, uncertainty, convergence, temporal effects, or multiple membership. |
| Workforce composition change evidence | Active PR #54 adds same-cutoff bitemporal composition-change evidence | `implemented_on_active_pr` | Buyers can review a proposed workforce change only after the exact PR earns checks and independent approval; it is not protected truth yet. |
| Organization hierarchy snapshot evidence | Active PR #56 adds bitemporal organization hierarchy snapshot evidence | `implemented_on_active_pr` | Organizational reporting remains an active integration lane, not a protected or released buyer workflow. |
| Selection-validity analysis handoff | Active PR #57 adds the governed handoff boundary for later validity estimation | `implemented_on_active_pr` | The handoff is not a statistical estimator and does not yet produce validity, bias, RMSE, coverage, or convergence evidence. |
| Role workspaces and Storybook runtime | Active PR #53 has the HR Home/Employee Profile fixture, an API-bound read-only Job Analysis view, and a local Storybook `10.5.10` build; protected `develop` still has no customer UI | `implemented_on_active_pr` | The component/state runtime and host-injected API boundary are reviewable, but there is no connected or released buyer workflow in protected truth. |
| Naruon calendar adapter | `packages/naruon-adapter` package tests; traceability says planned integration | `accepted_architecture` | Calendar intent is contract-tested, not an integrated customer scheduling workflow. |
| TEPP adapter | PR #52 is a non-executing request boundary; no transport contract is established | `implemented_on_active_pr` | Temporal analysis can be prepared as governed evidence but is not executed by Orgmetra. |
| Contextual Orchestrator/OpenCode model path | Named in architecture; no Orgmetra adapter or evidence-backed model evaluation in protected code | `planned` | LLM assistance cannot yet be invoked through an Orgmetra-owned, auditable draft-evidence boundary. |
| Search, semantic chunking, and image understanding | Architecture mentions derived search/vector storage, but no owned schema, chunker, OCR/object metadata, or index adapter is present | `planned` | Evidence retrieval cannot yet preserve paragraph/DOM/image location semantics for customer search. |
| Hot-partition scale strategy | No `PARTITION BY`/partition-management contract in the current migrations | `planned` | Append-heavy audit/outbox and temporal tables need a tested scale plan before high-volume production. |
| CSAP/SOC 2 evidence package | Security, threat, operability, and test documents exist; no control-evidence collection or attestation exists | `accepted_architecture` | The design is compliance-ready in intent, not a certification or audit report. |
| Release artifact | Root package is `0.1.0`; changelog remains `[Unreleased]`; no protected product release was verified | `planned` | Customers have no versioned, supportable Orgmetra product release yet. |

## Local candidate artifact outside protected truth

The current checkout contains `apps/hr-workspace/`, a dependency-free HR Home
and Employee Profile fixture based on Figma nodes `1:10` and `1:28`, plus an
API-bound read-only Job Analysis snapshot view. It uses
the shared design tokens and proves navigation, focus-visible styling,
keyboard-accessible evidence and confirmation dialogs, purpose-bound
permission denial, exact allocation values, and English/Korean labels. The
fixture explicitly displays that the protected People API is not connected.
The Job Analysis view requires a host-injected API base URL and authorization
provider, sends the existing purpose header, and has no synthetic fallback or
browser credential storage. The same active PR includes a local Storybook runtime with tokenized stories;
the current head has a passed Storybook build and local Playwright browser
smoke, but neither is connected People API integration, hosted deployment, or
protected-develop truth. The artifact must be reviewed, checked, and merged
independently before P0-1 can change maturity.

## Buyer gap backlog

| ID | Priority and owner | Gap and smallest acceptable closure evidence | Dependency |
|---|---|---|---|
| P0-1 | Product / Web | Review and merge the active HR Home + Employee Profile fixture and local Storybook states, then connect it to the protected People API and prove keyboard/focus/permission/confirmation states, exact-value tables, i18n, and browser E2E. | Protected People API evidence |
| P0-2 | Job Architecture | Protected `develop` now contains PR #38's persisted Job Analysis case/API, migration owner, ADR, versioned source evidence, and PostgreSQL acceptance tests. Active PR #53 adds the host-injected read-only browser boundary; connect it to a real API runtime, SME approval path, deployment, and browser evidence. | Protected People API evidence; active workspace path |
| P0-3 | Workforce Validation / scientific owner | Advance active PR #57 into a Rust-first estimator boundary or versioned adapter to `fast-mlsirm`/TEPP. Publish true-parameter recovery, bias, MAE, RMSE, coverage, convergence, temporal, multilevel, multiple-membership, CPU reference, and material GPU parity evidence. | Protected P0-2 and external contract re-resolution |
| P0-4 | Release / Platform | Produce a deployable release with version, changelog, migration inventory, rollback/recovery evidence, support runbook, and exact commit provenance. | P0-1 through P0-3 |
| P1-1 | Integration Hub | Implement contextual-orchestrator adapter for draft evidence only. Pin model/provider/config/evidence digests, use `NVIDIA_NIM_API_KEY` for model-backed development, and record ablations for single-route versus multi-agent depth/access lists. | P0-2; external runtime contract |
| P1-2 | Evidence Platform | Add normalized document/image segment metadata: semantic unit, source location, OCR/object tags, image reference, sensitivity, retention, embedding model/version, and owner provenance. Query filters must run before similarity ranking. | P0-2; document owner contracts |
| P1-3 | Data Platform | Define and rehearse hot-partition strategy for append-heavy audit/outbox and temporal facts, including tenant/time key choice, partition creation, retention, reindexing, and cross-partition query tests. | P0-1; production volume evidence |
| P1-4 | Trust / Operability | Build a CSAP/SOC 2 control matrix with owner, control activity, evidence location, retention, incident path, and release approval. Label it readiness evidence, never certification. | P0-1/P0-2 |

## Current open PR inventory and integration order

The following is the current GitHub inventory checked on 2026-08-21. All listed PRs target `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`. `REVIEW_REQUIRED` means the GitHub listing reported that review gate; it is not approval evidence. No self-approval or protection bypass is permitted.

| PR | Head branch / exact head | Scope | Current state | Next action |
|---:|---|---|---|---|
| 57 | `feat/validation-analysis-handoff` / `c38151852d95ff1256012d31c179a898bbc1c11e` | Governed selection-validity analysis handoff | Draft; merge state `BLOCKED`; `REVIEW_REQUIRED`; no submitted review; current workflows queued | Review the handoff boundary and keep estimator claims separate until exact-head checks and independent approval exist. |
| 56 | `feat/organization-hierarchy-snapshot` / `0eaa8c940842b3ba0d491f72ca57d4333c2c4d12` | Bitemporal organization hierarchy snapshot evidence | Draft; merge state `BLOCKED`; `REVIEW_REQUIRED`; no submitted review; current workflows queued | Verify tenant/time semantics and current-head checks before independent approval. |
| 55 | `fix/people-read-auth-backend-failure` / `f22225700723b46625372844a06205c3dc9b46e4` | People-read error normalization and pre-auth resource budgets | Draft; merge state `BLOCKED`; `REVIEW_REQUIRED`; current workflows queued | Strix's valid MEDIUM hire-route resource-boundary finding is repaired on this head; await terminal People API/security/recovery checks and independent approval. |
| 54 | `feat/workforce-composition-change` / `7d50e77d55bd908975754739f7f5f7e9422334c5` | Same-cutoff workforce composition change evidence | Ready; merge state `BLOCKED`; historical review threads resolved/outdated; no qualifying approval; current workflows queued | Re-fetch exact head, terminal checks, and qualifying independent approval before protected merge. |
| 53 | `codex/product-gap-baseline-workspace` / `88f809b030bb4ea2568810f1fd68bdc27d74c230` | HR Home + Employee Profile fixture, API-bound Job Analysis read view, Storybook, offer-approval integration, and baseline repair | Draft; merge state `BLOCKED`; `REVIEW_REQUIRED`; no submitted review; current workflows queued/pending | Keep the fixture/API boundary explicit, wait for all current-head checks, obtain independent approval, then decide whether to merge the product-surface slice. |
| 52 | `feat/tepp-analysis-adapter` / `3690e11516443ee82be88e69b042b5e0dbec80f5` | Governed TEPP analysis request boundary | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review thread resolved/outdated; current workflows queued | Keep non-executing and evidence-bound; merge only after exact-head checks and qualifying review. |
| 51 | `docs/protected-truth-refresh` / `b67a658cc98d58347db4995aba4858f0547ffccc` | Protected product-truth documentation repair | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review threads resolved/outdated; current workflows queued | Reconcile documentation with protected runtime truth, then use current-head checks and independent review. |
| 48 | `feat/governed-compensation-change-review` / `4d40a0d75cb3bba14e388f88bb418404540970b3` | Compensation review packet | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; no current review thread; current workflows queued | Verify high-impact confirmation/evidence boundaries, then merge only with terminal checks and independent approval. |
| 47 | `feat/governed-employment-leave-review` / `9ff50ca3eecfbd65d1b310ae783fc78ef5c1ba09` | Employment leave review packet | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; no current review thread; current workflows queued | Verify temporal and authorization contracts before protected merge. |
| 46 | `feat/governed-employment-separation-review` / `3e436f314c6fe256433db6cd3256e8eed3d6fed2` | Employment separation review packet | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review thread resolved/outdated; current workflows queued | Verify irreversible-action confirmation and audit evidence before protected merge. |
| 45 | `feat/governed-assignment-change-review` / `d89f82fb919039b57ea7f42993708961b7020299` | Assignment change review packet | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review threads resolved/outdated; current workflows queued | Verify tenant/person/employment/position binding before protected merge. |
| 44 | `feat/governed-performance-review` / `a8f319731f1f15f5ae391eb2178f4a642c150548` | Performance review packet | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review threads resolved/outdated; current workflows queued | Verify criterion scope and human confirmation before protected merge. |
| 42 | `feat/selection-outcome-monitoring-plan` / `ea8f62ab44b535b2d71bf6fa874b757bb777b72d` | Selection outcome monitoring | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; no current review thread; current workflows queued | Verify monitoring scope and temporal cohort semantics before protected merge. |
| 40 | `feat/structured-interview-plan` / `11838bcc88fd8afcc37ab0cbe3c6d8c5d8f19344` | Governed structured interview plan | Ready; merge state `BLOCKED`; `REVIEW_REQUIRED`; historical review threads resolved/outdated; current workflows queued | Verify human review, evidence versioning, and current-head checks before protected merge. |

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
| Protected `develop` contents | `git ls-tree` at `9e3e4847510e1e612b48474ba42b177b8ed824df` contains migration `0013`, Job Analysis API, ADR `0014`, candidate-evidence package, ADR `0025`, the protected offer-approval package, and their quality workflows. This proves repository presence, not deployment. |
| `npm run validate` on active PR #53 | Passed: foundation validation and 61 Node tests on exact local head `88f809b030bb4ea2568810f1fd68bdc27d74c230`. |
| Python package matrix on active PR #53 | Exact local head `c2d3a6c2804ab5a3e17e454312eddc2f96f2a72f`: HRIS kernel 171 passed; Job Analysis API 69 passed; People API 146 passed; candidate-evidence 75 passed; offer-approval 84 passed. All owned statement and branch coverage reports were 100%. |
| Storybook and browser fixture | Storybook `10.5.10` production build passed on prior exact workspace head `1d66f40778cc9900fd21df51a28b9109c600b754`; prior local browser smoke covered four action states, exact allocation values, locale switching, localized accessible names, and zero console/page errors. This remains local fixture evidence, not current protected deployment, People API integration, or released browser E2E; no current `c2d3a6c` Storybook rerun is claimed. |
| Protected-tree preservation | `git diff --name-status origin/develop..HEAD --diff-filter=D` returned zero deleted paths; protected Job Analysis migration/API/OpenAPI/quality-contract files remain present on the active PR branch. |
| PostgreSQL contracts | `tests/test_job_analysis_snapshot_postgres.sh` passed on exact local head `c2d3a6c2804ab5a3e17e454312eddc2f96f2a72f` against disposable PostgreSQL `16.14`; the full hosted PostgreSQL matrix remains the authoritative release gate. |

These results prove the current foundation contracts. They do not prove that open PRs are merged, that a browser UI exists, that a statistical estimator exists, or that Orgmetra is certified under CSAP/SOC 2.
