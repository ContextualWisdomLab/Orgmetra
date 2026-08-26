# Product and technical gap baseline

Inventory date: 2026-08-26 (Asia/Seoul). Default `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, approval evidence, or a substitute for fresh GitHub state. Every execution loop must refetch open PRs/issues, exact heads and independently resolved bases, dependency ancestry, formal reviews and unresolved threads, exact-head workflow/job checkout SHAs, effective rulesets, releases, and changed refs before acting.

Orgmetra owns authoritative HRIS/HCM truth only inside its published boundaries. Keyverse and the other dedicated-writer CWL repositories remain read-only dependencies consumed through published package/API/event contracts and existing owner-control paths. A static product-gap document never authorizes writes into another dedicated-writer repository.

## Effective repository-control truth

The effective control plane for default branch `develop` is organization ruleset **18156473 — `CWL Central required workflows`**, not the empty classic branch-protection payload by itself. Fresh repository reads on 2026-08-26 show the ruleset is `enforcement: active` and targets `~DEFAULT_BRANCH`.

The **current live ruleset is weaker than Orgmetra's acquisition-grade acceptance policy**:

- it requires **1** approving review, not two;
- `dismiss_stale_reviews_on_push = true`;
- `require_last_push_approval = false`;
- review-thread resolution and extra approval for unattributed changes remain enabled;
- the central required-workflow set plus deletion/non-fast-forward protection remain enabled; and
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

The following material owner lanes were freshly rechecked during the 2026-08-26 maintenance loop.

- **Oldest root PR #40** remains exact head `8d8896b14db10a5a4981f0b9e209ea00ee3be64c`. Orgmetra-native Structured Interview/Foundation/Recovery/SAST/Security evidence is GREEN, but formal OpenCode `CHANGES_REQUESTED` is current because the central `.github` coverage-evidence path double-wraps pytest-cov projects and later reports `No data was collected`. The existing foreign owner path is `.github#1250` / PR #1052; Orgmetra must not weaken local 100% coverage to compensate.
- **PR #54** has the same dedicated central coverage/review owner blocker while its Orgmetra-owned exact-head product/Foundation/security/recovery evidence is GREEN. It remains non-ready while that `CHANGES_REQUESTED` stands.
- **PR #75** owns governed HR export review evidence. Its exact-current-head local gates are GREEN, but live Draft state is controlled by the separate PR-lifecycle writer. **Child #120** owns audited one-time export egress and now fails closed on authorization-expiry races and ambiguous one-time publication through reconciliation-only recovery; it remains dependency-first and must not inherit parent evidence.
- **PR #92 → #121 → #125** is the performance-goal stack. #92 owns human-reviewed plan evidence; #121 owns authoritative activation and has focused exact-head GREEN; **#125 now owns durable activated goal-plan persistence** with exact reviewed/activation evidence-to-normalized-truth binding. #125 remains Draft with its exact-head persistence workflow queued, so none of this stack is shipped truth.
- **PR #118** owns non-authorizing release-readiness evidence. Its branch has advanced to exact head `eb529093b44be17bb282d3fd5c6c592d66f111af` with explicit src-layout package discovery. Release Readiness/Foundation/Recovery/SAST are GREEN on that head, while the current Security Scan is non-passing because the `osv-scan` job failed during `Set up job` before any source checkout or scan step. That pre-source failure is not converted into an Orgmetra product-code workaround, and no release authority is inferred from predecessor GREEN.
- **PR #124** owns the hardware-acceleration ADR security hardening. Hardware Acceleration ADR/Recovery/Job-Analysis/SAST/Security are GREEN on exact head `007c4133b60af46cc2a0771e5a393a86a2342a7d`, while Foundation CI remains queued; keep it non-passing until Foundation terminates successfully on the same head.
- **PR #123** owns customer-facing copy cleanup on exact head `382a46ac31222bf32980e27ed4c998a8ce019095`; every materialized exact-head Orgmetra workflow is GREEN and Devin reports zero issues, but there is still no qualifying independent approval.
- **PR #116** owns purpose-bound HR document retrieval, including authorization freshness through artifact verification, bounded content verification, audit-before-release, and hash-bound installed-artifact evidence.
- **PR #117** owns Job-Analysis-specific model-assisted Task/FJA/KSAO draft workflow; raw model output remains untrusted draft evidence and distinct accountable human review is mandatory.

Dependency-first descendants for qualification-rule persistence, Position reporting persistence, HR document persistence, offer-to-hire closure, Job-grade persistence, Position lifecycle application, Organization hierarchy application, Employment absence persistence, export execution, performance-goal activation, and performance-goal persistence remain active-PR truth only. Their focused GREEN evidence, where present, never transfers across parent integration or restack.

## Highest-value buyer gaps after the current owner lanes

Do not open withholding, payroll-pay, statutory accounting, year-end settlement, or foreign-service application tables inside Orgmetra without an accepted owner contract.

1. **Accessible buyer interaction for newer HRIS cores.** Job-grade, document, Position lifecycle/reporting, qualification-rule, absence, workforce-capacity, export and performance-goal capabilities need cohesive Product Design/Figma handoff, Storybook coverage, keyboard/focus/ARIA evidence, and customer-facing next-action copy when UI work is material. The existing HR workspace lane is an anchor, not permission to invent unavailable default-branch APIs.
2. **Authoritative release operation after governed readiness review.** PR #118 deliberately stops at `not_authorized_to_release`. No release/version/tag is authorized until one exact integrated `develop` head satisfies build/package/SBOM/provenance/reproducibility/compatibility/review/migration/rollback/recovery/accessibility/operational gates together, the live ruleset and qualifying approvals are freshly verified, and source/artifact hashes are rechecked. A future operation boundary must freshly authorize the exact integrated revision and fail closed rather than turning a review packet into release authority.
3. **Integration closure is itself a buyer risk until the dependency stacks land.** A capability implemented only on a stacked child is not commercially available product truth. Parent-first integration, fresh-base retargeting, migration/provenance reconciliation, and new exact-head local/central evidence are required before those capabilities can be represented as shipped.

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
