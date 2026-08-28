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
| #25 | Governed Job Analysis evidence boundary |
| #26 | `validity_study_case_record` integrity |
| #28 | Performance-criterion Job-scope guard |
| #31 | Governed People mutation API |
| #32 | Governed Naruon calendar intent adapter |
| #33 | Bitemporal workforce-composition evidence |
| #35 | Governed HRIS migration handoff |
| #38 | Governed Job Analysis snapshot persistence/read |
| #39 | Governed requisition review packet |
| #41 | Governed candidate evidence intake |
| #43 | Governed offer approval packet |

This is a selected shipped inventory, not a replacement for Git history. Do not describe active-PR capability as shipped until its owner PR integrates into fresh `develop`.

## Fresh active-owner truth

The following material owner lanes were freshly rechecked during the 2026-08-28 maintenance loop.

- **Oldest root PR #40** remains exact head `8d8896b14db10a5a4981f0b9e209ea00ee3be64c`. Orgmetra-native Structured Interview/Foundation/Recovery/SAST/Security evidence is GREEN, but formal OpenCode `CHANGES_REQUESTED` is current because the central `.github` coverage-evidence path double-wraps pytest-cov projects and later reports `No data was collected`. The canonical foreign owner handoff is **`.github#1250`**. The previously cited `.github#1052` implementation path is closed without merge and must not be represented as an active owner PR; Orgmetra must not weaken local 100% coverage or create a competing foreign repair.
- **PR #42** remains active at exact head `fca40417cfc60947a5836cf1a90815fdf118b889`. Its selection-monitoring package has local `116` tests and exact 100% statement/branch coverage, all review threads are resolved, and no qualifying approval is present. Its required OpenCode review check is terminal **FAILURE** because no current-head `opencode-agent` verdict was posted; this is a hosted review-orchestration blocker, not a leaf test failure. It remains active-PR truth only until fresh protected-base checks, independent approvals, and the required central gates complete.
- **PR #44** remains Draft at exact head `e011579f7191f41b500f017314c5ce6283e7d4e4`. Its performance-review package has local `84` tests and exact 100% statement/branch coverage, while repository validation passes; 44 hosted checks are attached with 37 success, 6 skipped, no active checks, and terminal `opencode-review` **FAILURE** because no current-head OpenCode verdict was posted. All review threads are resolved and no qualifying approval is present. It remains active-PR truth only and must not be described as shipped.
- **PR #54** has the same dedicated central coverage/review owner blocker while its Orgmetra-owned exact-head product/Foundation/security/recovery evidence is GREEN. It remains non-ready while that `CHANGES_REQUESTED` stands.
- **PR #141** has exact current head `93b10659346e5b6628f0510837d0df80928867ed` after enforcing same-tenant employing-organization scope in both Employment and confirmed-hire writes, with matching tenant-isolation regression coverage. Its exact-head hosted suite is terminal with 38 successful checks, 8 skipped checks, and 2 failures: `opencode-review` and `strix`; all current review threads are resolved and no qualifying independent approval exists. It remains active-PR truth and is not merge-authorized; no predecessor evidence is transferred.
- **PR #66** remains the unmerged normalized-application dependency at exact head `5f9c4700265f400830cfe00ad7e313ea26c61d70`. Its Foundation, candidate-application, PostgreSQL integrity, SAST, dependency, and security checks are terminal GREEN; exact-head `opencode-review` is terminal FAILURE for missing a current-head verdict, while the previous `strix` attempt is terminal FAILURE after contextual-orchestrator backend HTTP 500 responses and its failed-job rerun was cancelled before a runner job started. No authoritative Strix evidence was produced. All current review threads are resolved and no qualifying independent approval exists. Its source is active-PR truth only.
- **PR #67** now has exact current head `18bf097b2daefa61f30d127f513d32f1333360ca`, synchronized with normalized-application base `5f9c4700265f400830cfe00ad7e313ea26c61d70`. Its candidate-withdrawal audit envelope binds identity-resolution reference/digest, withdrawal evidence digest, and evidence version in addition to the withdrawal reference, while generic audit envelopes retain their existing contract. Foundation/manifest validation and 56 Node contract tests pass locally; exact-head Candidate Withdrawal PostgreSQL run `33156400198` / job `98800086944` is terminal GREEN across checkout, syntax, persistence, anti-forgery/tenant isolation, and read-only validation. It remains unmergeable as a dependency-first active PR because the parent is unmerged, `reviewDecision` is null, and no qualifying independent approval exists.
- **Required central Strix** remains an independent commercial merge gate. Authorized bounded fallback that completes authoritative structured analysis and terminal-successes the exact-head workflow is passing evidence (for example the existing #47/#48 positive canaries). Provider-chain exhaustion without an authoritative report remains non-passing (#42/#44/#45/#141 canaries) and belongs to the existing `.github#1327` owner path, not a leaf workaround. Central gateway remediation `.github#1369` and follow-up `.github#1378` are merged into protected `main` at exact merge commits `aca94fbf75f5820e1e0b71e8deb938f9d4ca8f09` and `cb369942be4cd7783753be45552d758ebaf79870`; current central `main` is `f6c2a2702b7b7578b2d1fc5f2f9a5125a0390d33`. These central Checks are not transferable proof for Orgmetra leaf PRs, and future central changes remain protected by the same terminal Strix and independent-approval requirements. A required Strix workflow that fails to materialize at all is likewise non-passing and belongs to that central owner boundary rather than an Orgmetra-local shim.
- **PR #53 → #130 with workflow-specific children #131, #132, #134, #135, #136, #137, #138, #139, and #140** is the HR Workspace accessibility stack. #53 owns the evidence-centered workspace anchor. #130 owns the shared protected-read interaction semantics required by Figma Storybook Inventory node `1:64`: loading/disabled/error/read-only/focus behavior, `aria-busy`, duplicate-submit prevention, explicit read-only evidence, concrete next actions, existing design-token usage, and `:focus-visible`. Its focused evidence is stack-local only.
  - **#131** owns one-time HR export delivery interaction: high-risk confirmation, duplicate-send prevention, read-only receipt, and reconciliation-only recovery after indeterminate delivery.
  - **#132** owns purpose-bound HR document retrieval interaction: authorization/loading, bounded artifact verification, audit-before-release, read-only handoff, expiry/denial/failure states, and value-minimized next-action copy.
  - **#134** owns Job-grade design-review interaction while retaining no compensation/promotion/assignment/candidate/employment-decision authority.
  - **#135** owns Position lifecycle human-review interaction while retaining no Position mutation authority.
  - **#136** owns qualification-rule human-review interaction while neither evaluating/ranking/rejecting/advancing a candidate nor authorizing an employment decision.
  - **#137** owns Position reporting-line human-review interaction while #94/#95/#106/#133 remain the separate reporting snapshot/review/persistence/structural-evidence owners. #137 exact head `b34e82fe36530525b4cbcb38e439f94b90d8cc89` has focused exact 100% line/branch/function GREEN.
  - **#138** owns Employment work-capacity human-review interaction while #103/#128 remain the separate governed-review/persistence owners. #138 exact head `9e3f5c5b1c959bef37831e8cba8695504a18061f` has `HR Workspace Work Capacity Review State Quality` run `33121181610` / job `98688132674` terminal GREEN: exact candidate checkout, 5 focused tests, **100% line/branch/function coverage**, and clean checkout. The UI records review semantics only; it does not mutate Employment truth or authorize compensation, scheduling, leave, payroll, or an employment decision.
  - **#139** owns reason-free Employment absence interaction while #113/#114 remain the separate bitemporal truth/persistence owners and #47 remains the separate leave-review owner. #139 exact head `cbbf975733c74413fe91310415c67a034090133d` has `HR Workspace Employment Absence State Quality` run `33125277888` / job `98701821651` terminal GREEN after a genuine contract-first RED on run `33125117860` / job `98701273064`. The UI exposes only read-only absent/not-absent operational evidence, never a reason, attendance/fitness inference, leave/scheduling/compensation authority, or employment-decision authority.
  - **#140** owns performance-goal human-review interaction while #92/#121/#125 remain the separate goal-plan review-evidence/activation/persistence owners. #140 exact head `260ddd27324aee5e67e09077e84a814b92d5891e` has `HR Workspace Performance Goal Review State Quality` run `33128554172` / job `98712427872` terminal GREEN after genuine contract-first RED run `33128460316` / job `98712125205`. The UI separates human review from activation, rating, compensation, and employment-decision authority and directs recorded review evidence to the separately governed activation boundary.
  - **#142 → #143** owns the Employee Profile bitemporal Assignment-history read and its presentation state boundary. #142 remains the backend read owner; #143 remains Draft and owns read-only loading/empty/denied/stale/error interaction only. Neither lane mutates Assignment truth or authorizes an employment decision.
  - **#144** owns the Candidate Evidence timeline presentation boundary on top of merged governed Candidate Evidence intake (#41). It remains Draft and read-only; it does not evaluate, rank, reject, advance, or authorize an employment decision.
  All UI children remain Draft dependency-first active-PR truth. Do not open a competing shared protected-read, one-time-export, document-retrieval, Job-grade, Position-lifecycle, qualification-rule, Position-reporting, Employment-work-capacity, Employment-absence, or performance-goal interaction writer.
- **PR #75 → #120** owns governed HR export review and audited one-time egress. #120 fails closed on authorization-expiry races and ambiguous one-time publication through reconciliation-only recovery. #131 is presentation evidence only and does not inherit or replace #75/#120 authorization, audit, or at-most-once delivery semantics.
- **PR #92 → #121 → #125** is the performance-goal backend stack. #92 owns human-reviewed plan evidence; #121 owns authoritative activation; #125 owns durable activated goal-plan persistence with exact reviewed/activation evidence-to-normalized-truth binding. #140 is presentation/interaction only and must not substitute for those authority boundaries. Child GREEN is stack-local only.
- **PR #103 → #128** is the Employment work-capacity backend stack. #103 owns human review evidence; #128 owns dependency-first durable persistence. #138 is presentation/interaction only and must never substitute for authoritative backend validation or mutation.
- **PR #113 → #114** is the Employment absence truth/persistence stack. Absence remains reason-free authoritative HRIS evidence and is distinct from work-capacity, leave-review, payroll, scheduling, and employment-decision semantics. #139 is presentation/interaction only and must never infer a reason, attendance/fitness, or consequential authority.
- **PR #118 → #126 → #127** owns the release-control stack end to end without authorizing a release from predecessor evidence. #118 owns readiness review, #126 exact-revision authorization, and #127 reconciled at-most-once publication. No parent checks/reviews transfer and the repository release collection remains empty.
- **PR #116** owns purpose-bound HR document retrieval, including authorization freshness through artifact verification, bounded content verification, audit-before-release, and hash-bound installed-artifact evidence. #132 mirrors only the customer interaction sequence.
- **PR #117** owns Job-Analysis-specific model-assisted Task/FJA/KSAO draft workflow; raw model output remains untrusted draft evidence and distinct accountable human review is mandatory.
- **PR #124** owns hardware-acceleration ADR security hardening at exact head `34a6520bf69731e69da27138e627ae774071376b`; local exact-head ADR/Foundation/Recovery/Job-Analysis/SAST/Security evidence is GREEN, while its live Ready-for-review state remains authoritative.

Dependency-first descendants for qualification-rule persistence, Position reporting persistence, HR document persistence, offer-to-hire closure, Job-grade persistence, Position lifecycle application, Organization hierarchy application, Employment absence persistence, export execution, performance-goal activation/persistence, Employment work-capacity persistence, Employment-separation approval, release authorization/publication, and all HR Workspace interaction children remain active-PR truth only. Their focused GREEN evidence never transfers across parent integration or restack.

## Highest-value buyer gaps after the current owner lanes

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Integrate the accessible buyer-interaction stack and retain the unowned P1 surfaces.** The currently named workflow-specific HR Workspace interaction gaps are owned under #53 → #130 by #131/#132/#134/#135/#136/#137/#138/#139/#140, while Employee Profile assignment history and the Candidate Evidence timeline now have the separate #142 → #143 and #144 owners. The PRD still names the Job Architecture workspace, hiring decision record, and Validation dashboard shell; the wireframe baseline also names HR Home, Job Architecture, Recruiting Workspace, Employee Profile, Validate, and Admin & Integrations. No shipped UI/Storybook integration is proven for these surfaces, so they remain active-PR or unowned planned gaps rather than protected-main truth. The commercial risk is dependency-first integration: land #53 and #130 first, then retarget/revalidate each child against fresh `develop`, reconcile intervening Storybook/Figma/UI changes, and obtain browser/accessibility/Foundation/Recovery/SAST/Security plus every applicable central exact-head gate before representing any child as shipped. Do not open a competing interaction writer for an already-owned scope.
2. **Integrated release-control closure, not another release boundary.** #118/#126/#127 already own readiness review, exact-revision authorization, and reconciled publication. The remaining commercial risk is integrating that dependency chain onto one fresh `develop` revision, then proving build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operability/security and central controls together before any tag/release is created. A parallel release writer would be duplicative and unsafe.
3. **Integration closure is itself a buyer risk until dependency stacks land.** A capability implemented only on a stacked child is not commercially available product truth. Parent-first integration, fresh-base retargeting, migration/provenance reconciliation, and new exact-head local/central evidence are required before those capabilities can be represented as shipped.

External finance/accounting and billing/collection integration remains planned/out-of-scope until an owner publishes a contract accepted into Orgmetra architecture/traceability. Orgmetra must not create statutory-account truth or direct cross-service application-table SQL as a shortcut.

## Technical non-negotiables

- Exact 100% owned production statement/branch coverage where tooling exposes it, plus beginner-readable public docs/docstrings and realistic security/privacy/concurrency/migration/recovery/accessibility cases.
- Descriptive two-or-more-word `snake_case` database objects and 3NF by default.
- Job, Position, Assignment, Employment, Organization, and Person remain distinct authoritative concepts.
- Business/effective time and system-recorded time remain separate; correction is correction-not-rewrite.
- Tenant/context isolation, opaque public correlation, least privilege, field minimization, encryption/retention/export controls, immutable audit-event and escalation evidence, and guarded mutable outbox transitions remain mandatory.
- Necessary PII remains usable only through purpose-bound authorization; indiscriminate masking is not a substitute for access control.
- High-impact employment decisions require accountable human confirmation with actor/purpose/reason/evidence versioning. LLM output remains untrusted draft evidence only.
- Preserve modular MSA extraction boundaries; do not introduce direct cross-service application-table SQL.
- Design toward CSAP and SOC 2 evidence readiness without claiming certification.
- Queued, pending, cancelled, skipped-required, neutral, absent, stale, predecessor, status-only, or model-only evidence is non-passing.

## Execution loop

Each run: refetch `develop`, all open PRs/issues and exact heads/bases, dependency ancestry, formal reviews/threads, exact-head workflows/jobs, releases, changed refs and effective rules; process oldest/dependency-root first; repair verified Orgmetra defects at the owning boundary test-first when an executable regression is appropriate; rerun exact-head evidence; resolve only addressed threads; and merge only when the unchanged head satisfies the effective ruleset, the commercial acceptance policy of at least two qualifying independent non-author approvals including approval after the last push with resolved conversations, and every applicable local/central gate.

For live-state documentation defects such as repository ruleset truth or active owner-lane ownership, do **not** hard-code a volatile external GitHub payload into an executable repository test merely to create artificial RED evidence. The regression is operational: each execution loop refetches the effective ruleset/current PR graph and rejects stale buyer copy before acting. Executable regressions remain required for code-owned behavior and stable repository contracts.

## References (APA 7th)

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).
