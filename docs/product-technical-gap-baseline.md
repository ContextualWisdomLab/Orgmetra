# Product and technical gap baseline

Inventory date: 2026-08-28 (Asia/Seoul). Default `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, approval evidence, or a substitute for fresh GitHub state. Every execution loop must refetch open PRs/issues, exact heads and independently resolved bases, dependency ancestry, formal reviews and unresolved threads, exact-head workflow/job checkout SHAs, effective rulesets, releases, and changed refs before acting.

Orgmetra owns authoritative HRIS/HCM truth only inside its published boundaries. Keyverse and the other dedicated-writer CWL repositories remain read-only dependencies consumed through published package/API/event contracts and existing owner-control paths. A static product-gap document never authorizes writes into another dedicated-writer repository.

## Effective repository-control truth

The effective control plane for default branch `develop` is organization ruleset **18156473 — `CWL Central required workflows`**, not the empty classic branch-protection payload by itself. Fresh repository reads on 2026-08-28 show the ruleset is `enforcement: active` and targets `~DEFAULT_BRANCH`.

The **current live ruleset is weaker than Orgmetra's acquisition-grade acceptance policy**:

- it requires **1** approving review, not two;
- `dismiss_stale_reviews_on_push = true`;
- `require_last_push_approval = false`;
- review-thread resolution and the central required-workflow set remain enabled;
- deletion and non-fast-forward updates remain prohibited; and
- `OrganizationAdmin` retains `bypass_mode=always`, while the connected user reports `current_user_can_bypass=always`.

Issue #89 owns the remaining repository-governance gap. Orgmetra's commercial acceptance remains stricter than the live ruleset: **at least two qualifying independent non-author approvals, approval after the last push, resolved conversations, every applicable exact-current-head local/central gate terminal GREEN, and no routine administrator bypass**. Organization-settings changes belong to the existing central owner-control path; Orgmetra must not simulate them with a workflow shim.

The classic branch payload can still report `protection.enabled=false`, required-status enforcement `off`, and no classic contexts/checks. That is **not** evidence that `develop` lacks an effective ruleset while organization ruleset 18156473 is active.

Consequences:

- GREEN or GitHub-mergeable is not merge authorization;
- queued, pending, cancelled, skipped, neutral, absent, stale, predecessor, status-only, or model-only evidence is non-passing;
- routine administrator bypass is not a normal merge path;
- a technically GREEN PR that another same-repository lifecycle writer has returned to Draft remains Draft until that authoritative writer advances it; and
- immediately before any future merge, refetch the unchanged exact head, live base, formal reviews, unresolved threads, effective ruleset, and every applicable exact-head check/job.

## Selected shipped buyer-visible anchors on `develop`

| Merged PR | Capability |
|---|---|
| #26 | `validity_study_case_record` integrity |
| #28 | Performance-criterion Job-scope guard |
| #31 | Governed People mutation API |
| #38 | Governed Job Analysis snapshot persistence/read |
| #41 | Governed candidate evidence intake |
| #43 | Governed offer approval packet |

This is a selected shipped inventory, not a replacement for Git history. Do not describe active-PR capability as shipped until its owner PR integrates into fresh `develop`.

## Fresh active-owner truth

The following material owner lanes were freshly rechecked during the 2026-08-28 maintenance loop.

- **Oldest root PR #40** remains exact head `8d8896b14db10a5a4981f0b9e209ea00ee3be64c`. Orgmetra-native Structured Interview/Foundation/Recovery/SAST/Security evidence is GREEN, but formal OpenCode `CHANGES_REQUESTED` is current because the central `.github` coverage-evidence path double-wraps pytest-cov projects and later reports `No data was collected`. The canonical foreign owner handoff is **`.github#1250`**. The previously cited `.github#1052` implementation path is closed without merge and must not be represented as an active owner PR; Orgmetra must not weaken local 100% coverage or create a competing foreign repair.
- **PR #54** has the same dedicated central coverage/review owner blocker while its Orgmetra-owned exact-head product/Foundation/security/recovery evidence is GREEN. It remains non-ready while that `CHANGES_REQUESTED` stands.
- **Required central Strix** remains an independent commercial merge gate. Authorized bounded fallback that completes authoritative structured analysis and terminal-successes the exact-head workflow is passing evidence (for example the existing #47/#48 positive canaries). Provider-chain exhaustion without an authoritative report remains non-passing (#42/#44/#45 canaries) and belongs to the existing `.github#1327` owner path, not a leaf workaround.
- **PR #53 → #130 with workflow-specific children #131, #132, #134, #135, #136, #137, and #138** is the HR Workspace accessibility stack. #53 owns the evidence-centered workspace anchor. #130 owns the shared protected-read interaction semantics required by Figma Storybook Inventory node `1:64`: loading/disabled/error/read-only/focus behavior, `aria-busy`, duplicate-submit prevention, explicit read-only evidence, concrete next actions, existing design-token usage, and `:focus-visible`. Its focused evidence is stack-local only.
  - **#131** owns one-time HR export delivery interaction: high-risk confirmation, duplicate-send prevention, read-only receipt, and reconciliation-only recovery after indeterminate delivery.
  - **#132** owns purpose-bound HR document retrieval interaction: authorization/loading, bounded artifact verification, audit-before-release, read-only handoff, expiry/denial/failure states, and value-minimized next-action copy.
  - **#134** owns Job-grade design-review interaction while retaining no compensation/promotion/assignment/candidate/employment-decision authority.
  - **#135** owns Position lifecycle human-review interaction while retaining no Position mutation authority.
  - **#136** owns qualification-rule human-review interaction while neither evaluating/ranking/rejecting/advancing a candidate nor authorizing an employment decision.
  - **#137** owns Position reporting-line human-review interaction while #94/#95/#106/#133 remain the separate reporting snapshot/review/persistence/structural-evidence owners. #137 exact head `b34e82fe36530525b4cbcb38e439f94b90d8cc89` has focused exact 100% line/branch/function GREEN.
  - **#138 now owns Employment work-capacity human-review interaction** while #103/#128 remain the separate governed-review/persistence owners. #138 exact head `9e3f5c5b1c959bef37831e8cba8695504a18061f` has `HR Workspace Work Capacity Review State Quality` run `33121181610` / job `98688132674` terminal GREEN: exact candidate checkout, 5 focused tests, **100% line/branch/function coverage**, and clean checkout. The UI records review semantics only; it does not mutate Employment truth or authorize compensation, scheduling, leave, payroll, or an employment decision.
  All UI children remain Draft dependency-first active-PR truth. Do not open a competing shared protected-read, one-time-export, document-retrieval, Job-grade, Position-lifecycle, qualification-rule, Position-reporting, or Employment-work-capacity interaction writer.
- **PR #75 → #120** owns governed HR export review and audited one-time egress. #120 fails closed on authorization-expiry races and ambiguous one-time publication through reconciliation-only recovery. #131 is presentation evidence only and does not inherit or replace #75/#120 authorization, audit, or at-most-once delivery semantics.
- **PR #92 → #121 → #125** is the performance-goal stack. #92 owns human-reviewed plan evidence; #121 owns authoritative activation; #125 owns durable activated goal-plan persistence with exact reviewed/activation evidence-to-normalized-truth binding. Child GREEN is stack-local only.
- **PR #103 → #128** is the Employment work-capacity backend stack. #103 owns human review evidence; #128 owns dependency-first durable persistence. #138 is presentation/interaction only and must never substitute for authoritative backend validation or mutation.
- **PR #113 → #114** is the Employment absence truth/persistence stack. Absence remains reason-free authoritative HRIS evidence and is distinct from work-capacity, leave-review, payroll, scheduling, and employment-decision semantics.
- **PR #118 → #126 → #127** owns the release-control stack end to end without authorizing a release from predecessor evidence. #118 owns readiness review, #126 exact-revision authorization, and #127 reconciled at-most-once publication. No parent checks/reviews transfer and the repository release collection remains empty.
- **PR #116** owns purpose-bound HR document retrieval, including authorization freshness through artifact verification, bounded content verification, audit-before-release, and hash-bound installed-artifact evidence. #132 mirrors only the customer interaction sequence.
- **PR #117** owns Job-Analysis-specific model-assisted Task/FJA/KSAO draft workflow; raw model output remains untrusted draft evidence and distinct accountable human review is mandatory.
- **PR #124** owns hardware-acceleration ADR security hardening at exact head `34a6520bf69731e69da27138e627ae774071376b`; local exact-head ADR/Foundation/Recovery/Job-Analysis/SAST/Security evidence is GREEN, while live Draft state remains authoritative.

Dependency-first descendants for qualification-rule persistence, Position reporting persistence, HR document persistence, offer-to-hire closure, Job-grade persistence, Position lifecycle application, Organization hierarchy application, Employment absence persistence, export execution, performance-goal activation/persistence, Employment work-capacity persistence, Employment-separation approval, release authorization/publication, and all HR Workspace interaction children remain active-PR truth only. Their focused GREEN evidence never transfers across parent integration or restack.

## Highest-value buyer gaps after the current owner lanes

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Complete accessible buyer interaction without duplicating the #130 child owners.** The shared protected-read state pattern is owned by #130 under #53; export delivery by #131; document retrieval by #132; Job-grade review by #134; Position lifecycle review by #135; qualification-rule review by #136; Position reporting-line review by #137; and **Employment work-capacity review by #138**. Another generic loading/error/read-only/focus writer or duplicate workflow-specific owner would be unsafe. The remaining workflow-specific Product Design/Figma/Storybook gaps are now **Employment absence** and **performance-goal** interaction, after their owner contracts are integrated or can be consumed without inventing unavailable default-branch APIs. Reuse #130's protected-read semantics and existing design tokens; add only workflow-specific keyboard/focus/ARIA, evidence provenance, and customer next-action behavior.
2. **Integrated release-control closure, not another release boundary.** #118/#126/#127 already own readiness review, exact-revision authorization, and reconciled publication. The remaining commercial risk is integrating that dependency chain onto one fresh `develop` revision, then proving build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operability/security and central controls together before any tag/release is created. A parallel release writer would be duplicative and unsafe.
3. **Integration closure is itself a buyer risk until dependency stacks land.** A capability implemented only on a stacked child is not commercially available product truth. Parent-first integration, fresh-base retargeting, migration/provenance reconciliation, and new exact-head local/central evidence are required before those capabilities can be represented as shipped.

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

Each run: refetch `develop`, all open PRs/issues and exact heads/bases, dependency ancestry, formal reviews/threads, exact-head workflows/jobs, releases, changed refs and effective rules; process oldest/dependency-root first; repair verified Orgmetra defects at the owning boundary test-first when an executable regression is appropriate; rerun exact-head evidence; resolve only addressed threads; and merge only when the unchanged head satisfies the effective ruleset plus every applicable local gate.

For live-state documentation defects such as repository ruleset truth or active owner-lane ownership, do **not** hard-code a volatile external GitHub payload into an executable repository test merely to create artificial RED evidence. The regression is operational: each execution loop refetches the effective ruleset/current PR graph and rejects stale buyer copy before acting. Executable regressions remain required for code-owned behavior and stable repository contracts.

## References (APA 7th)

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).