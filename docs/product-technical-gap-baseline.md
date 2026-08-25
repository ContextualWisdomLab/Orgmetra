# Product and technical gap baseline

Inventory date: 2026-08-25 (Asia/Seoul). Default `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This document is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, approval evidence, or a substitute for fresh GitHub state. Every execution loop must refetch open PRs/issues, exact heads and independently resolved bases, stack ancestry, formal reviews and unresolved threads, exact-head workflow/job checkout SHAs, effective rulesets, releases, and changed refs before acting.

Orgmetra owns authoritative HRIS employment truth inside its published boundaries. Keyverse and other dedicated-writer CWL repositories remain read-only dependencies consumed only through published package/API/event contracts and existing owner-control paths. No static product-gap document may authorize a write into another dedicated-writer repository.

## Effective repository-control truth

The effective control plane for default branch `develop` is organization ruleset **18156473 — `CWL Central required workflows`**, not the empty classic branch-protection payload by itself. Fresh repository reads on 2026-08-25 show this ruleset is `enforcement: active` and targets `~DEFAULT_BRANCH`, which includes Orgmetra `develop`.

The active ruleset requires:

- pull-request integration;
- **2 approving reviews**;
- dismissal of stale approvals after a push;
- approval after the last push;
- required review-thread resolution;
- extra approval for unattributed changes;
- the central required-workflow set from `ContextualWisdomLab/.github@main` (`close-empty-pr.yml`, `opencode-review.yml`, `pr-review-merge-scheduler.yml`, `security-scan.yml`, `strix.yml`, `sast-semgrep.yml`, and `noema-review.yml`);
- branch-deletion protection; and
- non-fast-forward protection.

Issue #89 remains open for two narrower commercial-control gaps. First, the effective ruleset still grants `OrganizationAdmin` an `always` bypass and the connected user reports `current_user_can_bypass=always`; routine administrator bypass is not an acceptable steady-state acquisition-grade control. Second, the ruleset does not itself enumerate every Orgmetra-local Foundation, Recovery, coverage/package/provenance, and product-quality gate, so merge readiness must continue to require fresh exact-head terminal GREEN for every applicable local gate unless fail-closed transitive enforcement is proven.

The classic branch payload may still report `protection.enabled=false`, required-status enforcement `off`, and no classic contexts/checks. That is **not evidence that `develop` has no effective protection** while ruleset 18156473 is active. Buyer-facing documents and PR metadata must not repeat that obsolete inference.

Consequences:

- a GREEN or GitHub-mergeable PR is not merge-authorized;
- two qualifying approvals and the last-push/review-thread rules remain mandatory;
- routine administrator bypass must not be used as a normal merge path;
- no workflow shim, author approval, predecessor check, status-only/model-only result, or force merge substitutes for the effective ruleset plus applicable exact-head local gates;
- immediately before any future merge, refetch the unchanged exact head, live base, formal reviews, unresolved threads, effective ruleset, and every applicable exact-head check/job.

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

## Fresh control anchors

The following anchors were freshly rechecked during the 2026-08-25 maintenance loop. They are intentionally sparse: an exhaustive static PR table becomes stale faster than it helps buyers or maintainers.

- **Oldest dependency-root PR #40** remains exact head `8d8896b14db10a5a4981f0b9e209ea00ee3be64c`, open, non-draft, mergeable, and exact-head GREEN for Structured Interview Plan, Foundation, SAST, Security, and Recovery. Submitted reviews are COMMENTED only; there is no qualifying `APPROVE`.
- **PR #54** remains exact head `cc6784ec33b1145c342bbbb99ebece1d37aeec80` with Orgmetra-owned product/Foundation/security/recovery evidence GREEN, but it is the sole open `CHANGES_REQUESTED` lane. The cited blocker is owned by the existing central `.github` coverage/review path (`.github#1250` / PR #1052), not an Orgmetra-native source failure. Keep that dependency boundary read-only from this loop.
- **PR #110** is exact head `305757e7daa3e8fd4d79ef385b42828e6f99d04c` and its People/Foundation/Recovery/SAST/Security/Job-Analysis gates are terminal GREEN. GitHub currently reports it Draft; prior event history shows a separate same-repository lifecycle writer repeatedly alternating Draft/Ready state, so this loop must not race that writer merely to change PR state.
- **PR #113** is exact head `3da7ad076f977a3ccd9e130a58786c9d26763a16` with Workforce/People/Job-Analysis/Foundation/Recovery/SAST/Security GREEN, but live GitHub state is Draft despite stale body text claiming Ready. Treat the live lifecycle state as authoritative and do not race the other writer.
- **PR #114** is the dependency-first child of #113 at exact head `656544bc4d86122ee42b50246500bf31785d6d53`; focused `Employment Absence Persistence Quality` is terminal GREEN. This is stack-local evidence only and cannot transfer parent checks/reviews or authorize integration before #113.

The repository currently has a large open PR graph. Execution order must come from a fresh oldest/dependency-root-first graph, not from recorded queue counts in this snapshot.

## Active-PR capabilities that are no longer buyer gaps

Several capabilities previously described as absent now have active owner lanes. They remain **active-PR truth, not default-branch truth**, until integrated.

- Job grade/band governance has a reviewed design-evidence root and a dependency-first bitemporal persistence child.
- Candidate offer response and offer-to-hire closure have active evidence/bridge lanes.
- Vacancy-to-Assignment fill orchestration is implemented on #110 and delegates final persistence to the authoritative People mutation boundary.
- Position lifecycle review/application and Position reporting review/persistence have active dependency-ordered lanes.
- HR document evidence and immutable document metadata persistence have active dependency-ordered lanes.
- Reason-free authoritative Employment absence truth is implemented on #113, with durable bitemporal persistence on child #114.

Do not describe these capabilities as shipped until their owner PRs integrate into fresh `develop`.

## Highest-value buyer gaps after the current queue

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Purpose-bound HR document retrieval/export execution.** Export-review and document-evidence/persistence lanes exist, but a customer still needs an authorized document read/egress execution boundary that re-resolves tenant/Person/Employment scope, purpose, permitted artifact/fields, retention/legal-hold state, destination, accountable human approval, and immutable audit before bytes leave the owner boundary.
2. **Job-Analysis-specific model-assisted draft workflow.** A generic Contextual Orchestrator draft-evidence boundary exists, but Job Analysis still needs a bounded workflow binding semantic-unit Task/FJA/KSAO draft provenance to an exact Job Analysis snapshot and explicit human confirmation before authoritative persistence. Model output remains untrusted draft evidence.
3. **Accessible buyer interaction for newer HRIS cores.** Job-grade, document, Position lifecycle/reporting, qualification-rule, absence, and workforce-capacity capabilities need cohesive Figma/Product Design handoff, Storybook coverage, keyboard/focus/ARIA evidence, and customer-facing next-action copy when UI work is material. The existing HR workspace lane is an anchor, not permission to invent unavailable default-branch APIs.
4. **Integrated release readiness.** Source SBOM/provenance, health/readiness, telemetry, and Kubernetes reference lanes exist, but no release/version/tag should be created until one exact integrated `develop` head satisfies all applicable build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operational gates together and source/artifact hashes are reverified.

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

Each run: refetch `develop`, all open PRs/issues and exact heads/bases, dependency ancestry, formal reviews/threads, exact-head workflows/jobs, releases, changed refs and effective rules; process oldest/dependency-root first; repair verified Orgmetra defects at the owning boundary test-first when an executable regression is appropriate; rerun exact-head evidence; resolve only addressed threads; and merge only when the unchanged head satisfies the effective ruleset plus every applicable local gate. Refresh this document only after material buyer/product state changes and never use its recorded SHAs as current control-plane truth.

For live-state documentation defects such as repository ruleset truth, do **not** hard-code a volatile external GitHub payload into an executable repository test merely to create artificial RED evidence. The regression is operational: each execution loop must refetch the effective ruleset and reject stale buyer copy before acting. Executable regressions remain required for code-owned behavior and stable repository contracts.

## 2026-08-24/25 operator diagnostics

- Repeated Strix failures have included NVIDIA NIM 429 saturation and a separate OpenCode app-token exchange 500 outage. Provider-unavailable runs are non-passing but do not imply a source defect without a scanner finding. Same-head reruns preserve exact-head semantics after transient recovery.
- Org review dispatch was previously disabled by `ORG_SWEEP_REVIEW_DISPATCH_LIMIT=0`; the central owner restored bounded dispatch. This remains foreign owner-control evidence, not permission for Orgmetra to mutate central `.github`.
- PR #54 demonstrates why source ownership matters: its Orgmetra-native gates are GREEN while the current blocking review cites a central coverage-evidence failure. Repair must stay at the existing central owner boundary.
- Review capacity remains the dominant integration constraint: the effective ruleset requires two qualifying approvals, while current Orgmetra open PRs have no qualifying `APPROVE` in the fresh review search.

## Doctoring (APA 7th)

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).
