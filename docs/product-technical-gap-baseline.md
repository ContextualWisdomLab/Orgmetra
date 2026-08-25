# Product and technical gap baseline

Inventory date: 2026-08-26 (Asia/Seoul). Default `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, approval evidence, or a substitute for fresh GitHub state. Every execution loop must refetch open PRs/issues, exact heads and independently resolved bases, stack ancestry, formal reviews and unresolved threads, exact-head workflow/job checkout SHAs, effective rulesets, releases, and changed refs before acting.

Orgmetra owns authoritative HRIS/HCM truth only inside its published boundaries. Keyverse and the other dedicated-writer CWL repositories remain read-only dependencies consumed through published package/API/event contracts and existing owner-control paths. A static product-gap document never authorizes writes into another dedicated-writer repository.

## Effective repository-control truth

The effective control plane for default branch `develop` is organization ruleset **18156473 — `CWL Central required workflows`**, not the empty classic branch-protection payload by itself. Fresh repository reads show the ruleset is `enforcement: active` and targets `~DEFAULT_BRANCH`.

The active ruleset requires pull-request integration, **2 approving reviews**, stale-approval dismissal after a push, approval after the last push, review-thread resolution, extra approval for unattributed changes, the central required-workflow set, branch-deletion protection, and non-fast-forward protection.

Issue #89 tracks the remaining acquisition-grade control gaps. `OrganizationAdmin` still has an `always` bypass and the connected user reports `current_user_can_bypass=always`; routine administrator bypass is not an acceptable steady-state commercial control. In addition, the effective ruleset does not itself enumerate every Orgmetra-local Foundation, Recovery, exact coverage/package/provenance, and product-quality gate, so merge readiness must continue to require fresh exact-head terminal GREEN for every applicable local gate unless fail-closed composition is directly proven. Finally, multiple technically GREEN PRs have been converted back to Draft by a separate same-repository lifecycle writer; this loop must not race that writer and must treat live lifecycle state as authoritative when that collision is evidenced.

The classic branch payload can still report `protection.enabled=false`, required-status enforcement `off`, and no classic contexts/checks. That is **not evidence that `develop` has no effective protection** while ruleset 18156473 is active.

Consequences:

- GREEN or GitHub-mergeable is not merge authorization;
- two qualifying approvals and the last-push/thread rules remain mandatory;
- routine administrator bypass is not a normal merge path;
- no workflow shim, author approval, predecessor check, status-only/model-only result, or force merge substitutes for the effective ruleset plus applicable exact-head local gates; and
- immediately before any future merge, refetch the unchanged exact head, live base, formal reviews, unresolved threads, effective ruleset, and every applicable exact-head check/job.

## Selected merged buyer-visible anchors on `develop`

| Merged PR | Capability |
|---|---|
| #26 | `validity_study_case_record` integrity |
| #28 | Performance-criterion Job-scope guard |
| #31 | Governed People mutation API |
| #38 | Governed Job Analysis snapshot persistence/read |
| #41 | Governed candidate evidence intake |
| #43 | Governed offer approval packet |

This is a selected shipped inventory, not a replacement for Git history. Do not revive merged heads; extend default-branch truth only through a current owner-scoped change when a fresh buyer gap remains.

## Fresh control anchors

The following anchors were freshly rechecked during the 2026-08-26 maintenance loop. They are intentionally sparse because an exhaustive static PR table becomes stale faster than it helps buyers or maintainers.

- **Oldest dependency-root PR #40** remains exact head `8d8896b14db10a5a4981f0b9e209ea00ee3be64c`, open, non-draft, mergeable, and exact-head GREEN for Structured Interview Plan, Foundation, SAST, Security, and Recovery. All fetched review threads are resolved and submitted reviews are COMMENTED only; there is no qualifying independent `APPROVE`.
- **PR #54** remains exact head `cc6784ec33b1145c342bbbb99ebece1d37aeec80` with Orgmetra-owned product/Foundation/security/recovery evidence GREEN, but it is the sole open `CHANGES_REQUESTED` lane. Its cited blocker is owned by the existing central `.github` coverage/review path (`.github#1250` / PR #1052), not an Orgmetra-native source failure. Keep that dedicated-writer boundary read-only from this loop.
- **PR #75** is exact head `a938a2a145e02db7f378533b9dea36167568c22b`, open, non-draft and mergeable. HR Data Export, Foundation, Recovery, SAST and Security are all exact-head GREEN. Its process-local issuance seal is explicitly defense in depth rather than durable serialization or export authority.
- **PR #110** is exact head `305757e7daa3e8fd4d79ef385b42828e6f99d04c` and its People/Foundation/Recovery/SAST/Security/Job-Analysis gates are terminal GREEN. GitHub has also reported it Draft after a separate same-repository lifecycle writer alternated Draft/Ready state, so this loop must not race that writer merely to change PR lifecycle state.
- **PR #113** is exact head `3da7ad076f977a3ccd9e130a58786c9d26763a16` with Workforce/People/Job-Analysis/Foundation/Recovery/SAST/Security GREEN, but live lifecycle state has been controlled by the separate lifecycle writer. Treat the live state as authoritative rather than trusting stale body copy.
- **PR #114** is the dependency-first child of #113 at exact head `656544bc4d86122ee42b50246500bf31785d6d53`; focused `Employment Absence Persistence Quality` is terminal GREEN. This is stack-local evidence only.
- **PR #119** is the dependency-first child of #96 at exact head `2d51b29b4788867c0656282c2ad8fea17c916e34`; focused `Organization Hierarchy Change Application Quality` is terminal GREEN after its TRUNCATE regression was corrected to exercise the table-owned append-only guard. It remains stack-local evidence only.
- **PR #121** is the dependency-first performance-goal activation child of #92. Predecessor head `b5815d7c470dab20192dbf590250417296b255fa` reached exact 100% owned statement/branch coverage but failed one test because a case-sensitive error regex expected lowercase `verification` while production correctly emitted the governed type name `PerformanceGoalPlanActivationVerification`. The minimal test-contract repair is exact head `a49df8a61baf406323f73e2e1a5f4fdd5d9c239f`; its new hosted evidence must be treated as non-passing until terminal on that exact head.

Execution order comes from a fresh oldest/dependency-root-first graph, not from recorded queue counts in this snapshot.

## Active-PR capabilities that are no longer unowned buyer gaps

The capabilities below remain **active-PR truth, not default-branch truth**, until integrated.

- Job grade/band governance has a reviewed design-evidence root and a dependency-first bitemporal persistence child.
- Candidate offer response and offer-to-hire closure have active evidence/bridge lanes.
- Vacancy-to-Assignment fill orchestration is implemented on #110 and delegates final persistence to the authoritative People mutation boundary.
- Position lifecycle review/application and Position reporting review/persistence have active dependency-ordered lanes.
- HR document evidence and immutable document metadata persistence have active dependency-ordered lanes.
- Reason-free authoritative Employment absence truth is implemented on #113, with durable bitemporal persistence on child #114.
- **Purpose-bound HR document retrieval is owned by PR #116.** It re-resolves exact tenant/document/Person/Employment/artifact/retention scope, requires purpose-bound authorization to remain current through artifact verification, verifies bounded bytes by SHA-256, appends value-minimized immutable audit evidence, and only then releases content.
- **Purpose-bound outbound HR export execution is now owned by Draft child PR #120 under #75.** The lane is distinct from retrieval: it freshly re-authorizes exact reviewed scope, materializes protected fields under a hard byte budget, commits value-minimized audit evidence before egress, rechecks authorization freshness after protected work and audit latency, and only then permits a host-owned one-time-download egress port. #120 is still based on an older #75 head, so it must not inherit the repaired parent evidence; #75 must integrate first and #120 must then retarget/revalidate on fresh `develop`.
- **Job-Analysis-specific model-assisted Task/FJA/KSAO drafting is owned by PR #117.** Raw model output remains untrusted draft evidence and a distinct accountable human reviewer is required.
- **Release-readiness review evidence is owned by PR #118.** It binds one exact candidate revision to source/SBOM/provenance/test/coverage/security/SAST/recovery/operability/accessibility/migration/rollback/package-reproducibility evidence and remains `not_authorized_to_release`.
- **Performance-goal authoritative activation is now owned by Draft child PR #121 under #92.** The activation boundary requires the reviewed human actor, exact scope re-verification, mutation-resistant plan evidence and a non-decision activation receipt. It remains dependency-first and non-integrated; authoritative durable goal-plan persistence is still a separate gap.
- Organization hierarchy parent-change application is implemented as dependency-first child #119 under review root #96; its focused bitemporal/RLS/audit/concurrency lane is GREEN but non-integrated.

Do not describe any of these capabilities as shipped until their owner PRs integrate into fresh `develop`.

## Highest-value buyer gaps after the current owner lanes

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Authoritative performance-goal persistence after activation.** PR #92 owns goal-plan review evidence and #121 owns the dependency-first activation boundary, but no current owner lane persists an activated plan as authoritative bitemporal performance-goal truth. Any future persistence lane must re-resolve Employment/Job/cycle scope, preserve goal/rating separation, require accountable human authority, bind the activation evidence version and append immutable audit/outbox evidence. Review or activation packets must not mutate authoritative truth by themselves.
2. **Accessible buyer interaction for newer HRIS cores.** Job-grade, document, Position lifecycle/reporting, qualification-rule, absence, workforce-capacity, export and performance-goal capabilities need cohesive Figma/Product Design handoff, Storybook coverage, keyboard/focus/ARIA evidence, and customer-facing next-action copy when UI work is material. The existing HR workspace lane is an anchor, not permission to invent unavailable default-branch APIs.
3. **Authoritative release operation after governed readiness review.** PR #118 owns non-authorizing release-readiness evidence, but no release/version/tag is authorized until one exact integrated `develop` head satisfies all applicable build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operational gates together, the live ruleset and qualifying approvals are freshly verified, and source/artifact hashes are rechecked. A future release operation must fail closed rather than converting a review packet into release authority.

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

For live-state documentation defects such as repository ruleset truth or active owner-lane ownership, do **not** hard-code a volatile external GitHub payload into an executable repository test merely to create artificial RED evidence. The regression is operational: each execution loop refetches the effective ruleset/current PR graph and rejects stale buyer copy before acting. Executable regressions remain required for code-owned behavior and stable repository contracts.

## References (APA 7th)

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).
