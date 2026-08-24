# Product and technical gap baseline

Inventory date: 2026-08-25 (Asia/Seoul). Default `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This document is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, branch-protection truth, or a substitute for fresh GitHub state. Every execution loop must refetch open PRs/issues, exact heads and bases, dependency ancestry, reviews/threads, exact-head workflows, effective repository rules, releases, and changed refs before acting.

Orgmetra owns authoritative HRIS employment truth inside its published boundaries. Keyverse and other dedicated-writer CWL repositories remain read-only dependencies consumed only through published package/API/event contracts and existing owner-control paths. No static product-gap document may authorize a write into another dedicated-writer repository.

## Repository-control truth

GitHub currently reports `develop` as `protected: true`, but the effective branch-protection payload observed for the same branch has `protection.enabled=false`, required-status enforcement `off`, and no required contexts/checks. Issue #89 owns that repository-settings defect.

Consequences:

- a GREEN PR is not merge-authorized merely because GitHub computes it as mergeable;
- qualifying independent non-author approval is still required where the repository governance contract requires it;
- no workflow shim, author approval, predecessor check, model-only status, or manual force merge substitutes for enforceable branch protection;
- immediately before any future merge, refetch the unchanged exact head, independently resolved live base, reviews, unresolved threads, effective rules/protection, and every applicable exact-head check.

## Merged buyer-visible anchors on `develop`

This is a selected shipped inventory, not a replacement for Git history.

| Merged PR | Capability |
|---|---|
| #26 | `validity_study_case_record` integrity |
| #28 | Performance-criterion Job-scope guard |
| #31 | Governed People mutation API |
| #38 | Governed Job Analysis snapshot persistence/read |
| #41 | Governed candidate evidence intake |
| #43 | Governed offer approval packet |

Do not revive these merged heads. Extend default-branch truth only through a current owner-scoped change when a fresh buyer gap remains.

## Live open-PR control snapshot

The repository currently has 68 open PRs. The examples below are anchors only; execution order comes from a fresh oldest/dependency-root-first graph.

### Oldest root gate

PR #40 (`8d8896b14db10a5a4981f0b9e209ea00ee3be64c`) is open, non-draft and mergeable. Structured Interview Plan, Foundation, SAST, Security, and Recovery are terminal GREEN on that exact head. Fresh reviews are COMMENTED only and the remaining unresolved threads are informational. It still has no qualifying independent non-author `APPROVE`, and issue #89's protection defect remains open, so it is intentionally unmerged.

### Dependency-constrained Draft descendants

These descendants remain Draft. Lane-local GREEN evidence is not integrated protected-base evidence and parent checks/reviews do not transfer.

| PR | Exact child head | Dependency |
|---|---|---|
| #58 | `c79a6ed49627e6a47947f171aeeed2bf02a8c152` | #57 |
| #67 | `cf59b3001fa58e5a978099c2a5692a03f4849fdd` | #66 |
| #77 | `9b02cb911377a5beb9f541e9acf2eb51ff065ee9` | #76 |
| #82 | `0c3a776f2e2c6f93c25e11c5c3ce3fa66a10b5c9` | #51 |
| #105 | `168f19402b3b17762cfe60f8a0e93c649a082989` | #104 |
| #106 | `c35ad114edbce7a4ebafcea793748493f1346351` | #94 |
| #107 | `5e521fd829de313a037f45ac28227c2ae5362d37` | #98 |
| #108 | `5027c772e5588b33e953258de008f0253389e95c` | #80 |
| #109 | `1eb17d1dbfa2ec822a9c6cce52d8a92b19ed9353` | #101 |
| #112 | `4f2a003769bf8f773559ac8122702f1451f0e8c0` | #111 |

Do not restack these descendants merely to manufacture fresh evidence while their parents remain unintegrated. After a parent integrates, retarget/reconcile the child against the then-current `develop`, refetch the resulting exact head/base/conflict state, and rerun all applicable Foundation/SAST/Security/Recovery/product gates without transferring predecessor evidence.

### Selected current root capabilities

The following are current open-root anchors with terminal exact-head GREEN evidence and are useful for product-gap reasoning. They remain unmerged pending live governance gates.

| PR | Exact head | Capability |
|---|---|---|
| #53 | `43ae3c73c0abef8f23d1c14f4e41d25b8c9b14df` | Evidence-centered HR workspace / Storybook slice |
| #75 | `282ff0966add47a80a2edd76f84c4c65a868fedb` | Governed HR data-export review |
| #80 | `5070f34cd13814f09d74162347f837cb34d76a57` | Candidate offer-response evidence |
| #81 | `78a9cb1e047db5c79ca855b992d44749b9214992` | Contextual Orchestrator draft-evidence boundary |
| #98 | `9aeeb204acce429f85b028029c9531a5b05f37e1` | Governed HR document evidence |
| #99 | `fff082f56e34e47cb83a19316d132c5638d3b633` | Employment-scoped bitemporal base compensation |
| #101 | `13c4cf8ee7e91ffa0ac1a33fdc9461e4c31d5fb2` | Governed Job-grade design review |
| #102 | `d87cb05f723f106c653f2ea07680872fd9c62ada` | Purpose-bound audit-evidence review |
| #104 | `d92ac4cb798b3bd32b632c0ab677c03f944070e4` | Governed Job qualification-rule review |
| #110 | `bc84eaa145166a3f77a57f0c94c6d7459cfc65f3` | Vacancy-to-Assignment fill orchestration |
| #111 | `cfff42f5cf884ff67169ddeff645c6933e19337a` | Governed Position lifecycle-change review |

This table intentionally does not assert that every root is merge-authorized. Fresh review and effective-rule state remain authoritative.

## Buyer-visible progress since the previous snapshot

Several items that were previously listed as unresolved product gaps now have active owner lanes and must no longer be described as absent:

1. **Job grade/band governance:** #101 provides reviewed Job-grade design evidence; #109 is the dependency-first bitemporal persistence descendant.
2. **Offer-to-hire close:** #80 owns candidate offer-response evidence; #108 is the dependency-first bridge to the authoritative confirmed-hire boundary.
3. **Vacancy-to-Assignment fill:** #110 owns the current orchestration slice and delegates final persistence to the authoritative People mutation boundary.
4. **Position lifecycle:** #111 owns human-reviewed lifecycle-change evidence; #112 is the dependency-first authoritative application descendant.
5. **HR document evidence:** #98 owns the value-minimized evidence packet; #107 is the dependency-first immutable persistence descendant.

These are active-PR capabilities, **not protected-main truth** until integrated.

## Highest-value buyer gaps after the current queue

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Purpose-bound HR document retrieval/export execution.** #75 reviews export intent and #98/#107 govern document evidence/persistence, but a customer still needs an authorized document read/egress execution boundary that re-resolves tenant/Person/Employment scope, purpose, permitted fields/artifact, retention/legal-hold state, delivery destination, human approval, and immutable audit before bytes leave the owner boundary.
2. **Authoritative Employment leave/absence truth.** #47 provides a governed leave review packet, but protected `develop` still lacks a normalized bitemporal leave/absence application/persistence boundary that preserves Employment scope, business time, system-recorded time, human review, correction-not-rewrite history, tenant isolation, and audit/outbox evidence without turning policy review into payroll or scheduling authority.
3. **Job-Analysis-specific model-assisted draft workflow.** #81 provides the generic Contextual Orchestrator draft-evidence contract; a later Job Analysis slice should bind semantic-unit Task/FJA/KSAO draft provenance to an exact Job Analysis snapshot workflow and require explicit human confirmation before authoritative persistence. Model output remains untrusted draft evidence.
4. **Accessible buyer interaction for the newer HRIS cores.** Job-grade, document, Position lifecycle/reporting, and qualification-rule capabilities need cohesive Figma/Product Design handoff, Storybook coverage, keyboard/focus/ARIA evidence, and customer-facing next-action copy when UI work is material. #53 is a useful existing workspace anchor rather than permission to invent protected-main API behavior.
5. **Integrated release readiness.** Source SBOM/provenance, probes, telemetry and Kubernetes reference lanes exist, but no release/version/tag should be created until one exact integrated protected head satisfies applicable build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operational gates together and source/artifact hashes are reverified.

External finance/accounting and billing/collection integration remains planned/out-of-scope until an owner publishes a contract accepted into Orgmetra architecture/traceability. Orgmetra must not create statutory-account truth or direct cross-service application-table SQL as a shortcut.

## Technical non-negotiables

- Exact 100% owned production statement/branch coverage where tooling exposes it, plus beginner-readable public docs/docstrings and realistic security/privacy/concurrency/migration/recovery/accessibility cases.
- Descriptive two-or-more-word `snake_case` database objects and 3NF by default.
- Job, Position, Assignment, Employment, Organization, and Person remain distinct authoritative concepts.
- Business/effective time and system-recorded time remain separate; correction is correction-not-rewrite.
- Tenant/context isolation, opaque public correlation, least privilege, field minimization, encryption/retention/export controls, and immutable audit/outbox remain mandatory.
- Necessary PII remains usable only through purpose-bound authorization; indiscriminate masking is not a substitute for access control.
- High-impact employment decisions require accountable human confirmation with actor/purpose/reason/evidence versioning. LLM output remains untrusted draft evidence only.
- Preserve modular MSA extraction boundaries; do not introduce direct cross-service application-table SQL.
- Design toward CSAP and SOC 2 evidence readiness without claiming certification.
- Queued, pending, cancelled, skipped-required, neutral, absent, stale, predecessor, status-only, or model-only evidence is non-passing.

## Execution loop

Each run: refetch `develop`, all open PRs/issues and exact heads/bases, dependency ancestry, reviews/threads, exact-head workflows, releases and effective rules; process oldest/dependency-root first; repair verified Orgmetra defects at the owning boundary test-first when practicable; rerun exact-head evidence; resolve only addressed threads; and merge only with qualifying independent non-author approval plus actually enforceable protection. Refresh this document only after material state changes and never use its recorded SHAs as current control-plane truth.

## 2026-08-24/25 automation findings (operator diagnostics)

1. **Strix failures were infrastructure, not source defects.** Repeated `strix` failures traced to NVIDIA NIM `429 Too Many Requests` during scanner LLM connection (three primary attempts plus fallback exhausted, no report artifact, fail-closed). Local exact-head verification reproduced all owned package suites green at 100% statement/branch coverage; the scan lane, not the code, was failing. Remediation: staggered same-head re-scan dispatch (`repository_dispatch strix-scan`) instead of concurrent bursts.
2. **Org review-dispatch budget was zero.** `ORG_SWEEP_REVIEW_DISPATCH_LIMIT` was `0`, so the org queue sweep could never dispatch an OpenCode review anywhere. Restored to `2` with `ORG_SWEEP_BRANCH_UPDATE_LIMIT=1`; `ContextualWisdomLab/Orgmetra` added to the central targeted-dispatch allowlist. Diagnose future zero-review stalls against this variable first.
3. **Strix gate semantics after a completed scan.** A real reported vulnerability fails the required check by design. PR #52's first completed scan surfaced one legitimate MEDIUM IDOR-shaped finding (cross-field reference validation missing in `TeppAnalysisRequestPacket`); repaired at head `e068df7` with temporal ordering, distinct workspace/snapshot identifiers, and a scope digest binding every retry-stable correlation. Scanner finding -> test-first root repair -> fresh full-head evidence is the intended loop.
4. **Shared-credential saturation is the remaining systemic constraint.** The OpenCode GitHub App installation token hits GitHub API rate limits mid-sweep before reaching later repositories, and NVIDIA NIM 429s arrive org-wide because one key is shared. Both are transient retryable infra states, never source defects; a scan can complete with zero vulnerabilities yet fail closed on one transient backend signal in its console output.

## Doctoring (APA 7th)

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).
