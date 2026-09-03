# Product and technical gap baseline

Verified: 2026-09-03 (Asia/Seoul) for Orgmetra protected/product refs. External owner-repository evidence retains its separately dated doctoring until re-fetched in that owner lane.

This document is the commercialization baseline for **Orgmetra**, not a frozen PR inventory and not merge authorization. It records product responsibility, shipped-vs-planned truth, causal control-plane blockers, and the next highest-leverage buyer gaps. Volatile PR heads, workflow run IDs, queue counts, review snapshots, mergeability, and base tips must be fetched live before every action rather than copied here until stale.

## 1. Product thesis and buyer outcome

Orgmetra is the ContextualWisdomLab evidence-centered HRIS/HCM system of record. Its commercial value is not another employee database: it preserves **what employment fact was true, when it was true, which evidence justified a high-impact decision, who acted, what purpose authorized access, and how later outcomes validate the original job/selection model**.

Primary buyer/user roles from the PRD are HR operations owners, HRIS administrators, recruiters, hiring managers, job-analysis specialists, psychometricians/people-analytics scientists, compliance/audit reviewers, workers, and enterprise integration engineers.

The buyer-facing lifecycle is:

1. govern job requirements and evidence;
2. collect candidate evidence without turning opaque references into decision authority;
3. record accountable human selection and offer decisions;
4. convert a selected candidate into authoritative worker/employment/assignment truth without losing provenance;
5. observe job-relevant performance over effective and system time;
6. validate selection evidence against later outcomes and fairness evidence; and
7. expose purpose-bound, auditable workflows through stable APIs and role workspaces.

## 2. Truth-state contract

Every feature claim must use one of these states. A documentation-only design is never promoted to shipped truth.

| State | Meaning |
| --- | --- |
| **Shipped truth** | Present on protected `develop` with executable evidence. |
| **Active PR** | Implemented only on an open exact PR head; predecessor or sibling evidence does not transfer. |
| **Accepted architecture** | Accepted ADR/PRD/TRD boundary whose production implementation is incomplete. |
| **Planned** | Prioritized buyer capability with no executable production evidence yet. |
| **Research-only** | Evidence or experiment that must not be represented as product behavior. |
| **Superseded** | Replaced decision/evidence; retain only for provenance. |
| **Out of scope** | Owned by another bounded context/repository or explicitly rejected. |

Merge, release, deployment, and compliance claims require fresh exact-head evidence independently of this file.

## 3. Domain ownership and context map

Orgmetra owns **authoritative employment truth**. It must not become a monolithic copy of specialist products.

| Bounded context | Orgmetra responsibility | Integration boundary |
| --- | --- | --- |
| `people_core` | person anchors, employment, assignments, compensation references, candidate-worker linkage | Keyverse provides identity, not HRIS truth |
| `organization_core` | legal/organization units, reporting relations, locations, positions | external org identities remain referenced, not copied wholesale |
| `job_architecture` | jobs, tasks, FJA/KSAO evidence, qualification rules, SME approval, governed snapshots | ontology sources and contextual-orchestrator are evidence/draft adapters |
| `talent_acquisition` | requisitions, candidates, interviews, immutable decision-evidence sets, selection/offer governance | specialist assessment systems remain external evidence owners |
| `performance_management` | cycles, criterion blueprints, observations, calibration | observations bind authoritative worker/job/time scope |
| `workforce_validation` | validity-study registry, exact predictor/criterion links, subgroup/drift evidence, scientific adapters | fast-mlsirm/TEPP/Psychometrics Commons own specialist numerical/psychometric computation |
| `document_records` | canonical document/image metadata and immutable artifact references | Clearfolio/NewsDOM-style document services are adapters |
| `integration_hub` | idempotency, inbox/outbox, adapter state, migration/CDC boundary | Naruon, migration tools, and peer CWL systems remain behind versioned ACLs |
| `audit_provenance` | append-only audit/provenance evidence | no peer service may silently become authoritative HRIS state |

The initial deployment may share one PostgreSQL cluster, but each bounded context keeps an owned schema, role, migrations, generated access layer, and contract. Cross-context application-table reads are prohibited; versioned API/event/adapters form the anti-corruption layer. A shared physical database is not a Shared Kernel license.

## 4. Current protected-branch product truth

Protected `develop` was freshly observed at `ef1b143368cb6249c9520ca8cae10ebe844a5aa1`. This SHA is a dated evidence anchor only; every execution loop must re-fetch the branch before acting. The latest protected change restores Foundation CI and Recovery Rehearsal Quality documentation-content checks after the preceding docs-only path exclusions proved unsound: both workflows hash or otherwise validate governed documentation/traceability artifacts, so docs-only changes must remain in their admission scope. This protected workflow repair does not promote any pending HR domain feature to Shipped truth.

Shipped foundation evidence includes:

- bitemporal HRIS, tenant-isolation/RLS, evidence-sealing, audit/outbox and persistence contracts;
- governed candidate/selection/requisition/offer and job-analysis evidence packages;
- purpose-bound authorization and normalized employment/assignment/performance foundations;
- Keyverse/Naruon/migration adapter boundaries and design-token foundations; and
- PRD/TRD/ADR/UML/ERD/security/test/operability documentation sufficient to define intended modular boundaries.

Protected `develop` does **not** yet encode the HR decision that distinguishes a primary assignment from a concurrent secondary/TFT assignment. Allocation percentage, row order, position identity and graph topology are not classification authority. Orgmetra issue #162 and Draft PR #163 are the active `people_core` owner lane: new writes require explicit `primary | concurrent_secondary`; pre-contract history remains `legacy_unspecified` without inference; one tenant-local Employment may have at most one simultaneously visible primary assignment for one effective/system-time coordinate; category participates in semantic idempotency; and API/application/PostgreSQL boundaries must enforce the same vocabulary. Because #163 is still an Active PR with non-terminal exact-head evidence, none of that behavior is Shipped truth yet. The #163 branch has non-force adopted the current protected workflow truth rather than retaining the superseded docs-only exclusions.

Assignment category correction is a distinct dependent buyer gap rather than an implied capability of #163. Issue #164 and Draft PR #165 own immutable close → replacement → normalized predecessor/replacement supersession for already-committed explicit categories. The active child preserves tenant/Employment/Person/Position/allocation/effective truth, requires Keyverse purpose-bound authorization and human-confirmation/evidence metadata, records audit/outbox plus durable replay evidence in the same PostgreSQL transaction, and rejects caller-defined command/authorization-decision/result runtime subtypes at their trust boundaries. Its correction-specific recorded-time ingress now also resolves an exact aware `datetime` offset once and detaches accepted caller-owned `tzinfo` behavior onto a built-in fixed-offset timezone; provider failures, offsetless evidence and executable `timedelta` subtypes fail closed under the correction error contract. The dedicated exact-head workflow executes that regression, but the child remains downstream of #163 with non-terminal hosted evidence, so correction provenance is **Active PR**, not Shipped truth.

The root package remains `orgmetra-foundation-pack` version `0.1.0`, private, with a validation-oriented script rather than a deployable buyer application. Current default-branch code search finds `orgmetra-gateway`, employee workspace and HR workspace as architecture/design references, while no React implementation is indexed. The P1 PRD promise—Job Architecture, Candidate Evidence, Hiring Decision, bitemporal Employee Profile and Validation workspaces—therefore has **no protected-branch buyer UI implementation evidence yet**. Treat this as a major commercialization gap, not as a documentation completion.

There are currently no published GitHub releases. Do not manufacture a release merely to clear that count; release only when an integrated protected head has complete exact-head governance, security, operability and buyer-workflow evidence.

## 5. Effective GitHub governance: P0 release blocker

The effective control plane for Orgmetra `develop` is inherited organization ruleset **18156473 — `CWL Central required workflows`**. Classic branch-protection fields alone are not authoritative while that ruleset is active.

Fresh Orgmetra live reads on 2026-09-03 show the inherited ruleset still has:

- `required_approving_review_count = 1`;
- `require_last_push_approval = false`;
- `require_code_owner_review = false`;
- `required_reviewers = []`;
- `dismiss_stale_reviews_on_push = true`;
- required review-thread resolution enabled;
- central required workflows enabled;
- only merge and squash allowed;
- deletion and non-fast-forward protection enabled; and
- an `OrganizationAdmin` actor with routine `bypass_mode = always`.

The central `.github` repository's own active ruleset **17921150 — `Lock default branch`** is a second live drift surface. Its approval count is already `0`, last-push approval and CODEOWNER review are disabled, required reviewers are empty, review-thread resolution and deletion/non-fast-forward protection are enabled, but it still permits `rebase` and still exposes `OrganizationAdmin/always` bypass. Source-level audit policy and both live ruleset payloads must converge before governance repair is complete.

This is not the current governance decision. `.github#772` establishes that the present one-human-maintainer fleet cannot satisfy a positive generic independent-human approval count, a last-push approval by another person, or mandatory CODEOWNER approval by the same sole author. The compliant repair is **not** a bot approval, service-account approval, self-approval, credential widening, or routine administrator bypass. The current target is:

- `required_approving_review_count = 0` while no genuinely independent human reviewer exists;
- `require_last_push_approval = false` because the rule otherwise requires a different person from the latest pusher;
- `require_code_owner_review = false` while the sole code owner is also the author;
- no synthetic `required_reviewers` merely to recreate the unavailable human gate;
- review-thread resolution stays enabled;
- exact-current-head OpenCode, Noema, Strix, Security/SAST, Dependency Review, coverage, provenance and repository-specific quality gates remain fail-closed;
- deletion and non-fast-forward protection remain enabled;
- no routine `OrganizationAdmin/always` bypass; emergency repair belongs to a separately governed, time-bounded, auditable break-glass path; and
- only merge and squash are accepted by the current audit; merge-method policy must not be weakened merely to solve the reviewer-capacity problem.

Causal owner: `ContextualWisdomLab/.github`. Issue #772 defines the satisfiable one-human policy and #1351 tracks fleet reconciliation. Retired #1176 is predecessor evidence only after verified complete carryover of every valid audit delta into the single active owner-plane/audit writer, **PR #1644**. PR #1644 pins exactly rulesets 17921150 and 18156473, refuses identity/provenance drift, preserves unrelated controls, binds privileged mutation to the exact protected-main SHA, verifies immutable ruleset history, treats ambiguous PUT outcomes as unresolved until history/live-state evidence proves convergence, and uses a separately provisioned protected-environment `CWL_RULESET_ADMIN_TOKEN` rather than widening ordinary repository credentials. Its current exact-head focused governance suite has reached terminal success after non-force reconciliation with protected `main`, while the broader security fleet remains non-terminal; focused success is not full merge authority. Source integration alone is intentionally insufficient: after #1644 reaches protected `main`, a controlled maintenance interval must provision the least-privilege owner-plane credential, enable `CWL_RULESET_RECONCILE_ENABLED`, perform and verify the mutation, disable/retain the reconciler according to the reviewed drift-repair policy, and then re-run the canonical audit plus Orgmetra canary. Orgmetra issue #89 mirrors this dependency. Orgmetra must not add a leaf workflow shim to simulate organization settings.

The #1644 owner-plane lineage has already repaired deterministic test-contract drift, collision/recovery ambiguity, post-settlement version races, and protected-main integration without force-push. Every later protected-main reconciliation resets exact-head evidence, so only the current unchanged writer head may authorize ordinary integration. Completed one-shot source-fix machinery is absent from the current owner tree.

**Canary:** Orgmetra PR #88 (`fix/job-analysis-http-request-budgets`) was freshly re-verified on exact head `0dc4f09cc3c87829ea1e3a0e3dc0188df07ad8cd`; the currently returned repository workflow runs are terminal-success, combined CodeRabbit/Devin statuses are successful, and its only inline review thread is resolved. It has no qualifying independent approval. It is intentionally retained as a governance canary: after the central policy repair, an unchanged sole-author GREEN PR must no longer be blocked *only* by a reviewer identity that does not exist. Repository-native auto-merge is currently disabled for Orgmetra, so that setting cannot be used to disguise the admission defect. Do not merge it through administrator bypass to fake that proof.

## 6. Required-workflow availability: P0 evidence blocker

The central Dependency Review workflow must fail closed: it may proceed to the pinned GitHub Dependency Review action only after an exact immutable `BASE_SHA...HEAD_SHA` dependency comparison returns transport success and authenticated HTTP `200`.

The temporary `.github#1643` diagnostic completed its evidentiary purpose: on one unchanged exact-head A/B canary, the anonymous dependency comparison returned HTTP `404` while the same exact repository/base/head comparison using a minimally scoped job token with `contents: read` + `pull-requests: read` returned HTTP `200`, both with successful transport. Therefore anonymous responses are not availability authority. The canonical current owner is Draft **`.github#1725`**, which carries the valid diagnostic deltas without the temporary canary: reusable callers explicitly grant the least-privilege permission envelope, repository/base/head values must be legal immutable identities before transport, only authenticated HTTP 200 authorizes `actions/dependency-review-action`, and every authenticated non-200 remains fail-closed. Exact-head security evidence for #1725 remains non-terminal, so none of this owner repair is protected/released truth yet.

Orgmetra must not infer a clean dependency review from independent OSV, Trivy or Scorecard success, and it must not create a leaf skip. After #1725 reaches protected `ContextualWisdomLab/.github/main` through ordinary protection, consumers must pin the released immutable owner workflow identity and prove an unchanged public non-fork exact comparison returns HTTP 200 and the pinned Dependency Review action materially executes.

## 7. Current baseline-writer evidence

PR #100 owns this baseline. A predecessor exact head failed Foundation/Recovery-family repository-contract checks after `.codegraph/` was added to `.gitignore` without resealing `manifest.json`. The owner branch was repaired by resealing only the `.gitignore` manifest entry to the exact current digest/size/line count. The branch has now non-force adopted protected `develop@ef1b143368cb6249c9520ca8cae10ebe844a5aa1` through a two-parent merge. That protected change reverts #166's docs-only workflow exclusions because Foundation and recovery admission contain documentation-content contracts; the baseline therefore no longer carries or describes those exclusions as current truth.

Do **not** store PR #100's own current head inside this file: changing this file creates a new head and would make the value self-invalidating. Its PR body and GitHub API are the source for exact-current-head verification. All reviews/checks must be re-fetched after every push.

## 8. Commercialization gap register

| Gap | Current evidence | Buyer consequence | Owner / next acceptance evidence | Priority |
| --- | --- | --- | --- | --- |
| **GOV-01 satisfiable protected-branch admission** | live inherited ruleset still requires one unavailable generic approval and routine admin bypass; owner-repository ruleset still permits rebase and routine admin bypass; retired #1176 has transferred its valid audit deltas into active #1644, whose focused current-head governance validation succeeds while broader evidence remains non-terminal | GREEN work cannot progress normally; bypass would undermine evidence | `.github#772/#1351/#1644`; terminal unchanged-head evidence → protected-main integration → least-privilege maintenance apply → immutable-history/full live-payload convergence → canonical audit + unchanged Orgmetra #88 ordinary-path proof | **P0** |
| **SEC-01 authoritative Dependency Review availability** | decisive A/B showed anonymous 404 vs minimally scoped job-token 200; canonical Draft #1725 keeps authenticated non-200 fail-closed, explicit caller permissions and immutable identity validation, but is not yet protected/released | merge queue can remain blocked without trustworthy dependency diff | `.github#810/#1725`; terminal unchanged-head evidence → ordinary protected integration → immutable consumer pin → unchanged public non-fork authenticated comparison 200 + pinned action execution | **P0** |
| **REL-01 integrated release evidence** | no published release; large active PR stack; no single integrated protected head yet proves the complete gate set | buyers cannot install/deploy a supported release | merge causal dependency roots in order; protected-head release checklist + signed/provenance evidence + CHANGELOG/version | **P0** |
| **ASG-01 explicit assignment authority** | protected `develop` stores assignment allocation but not the explicit HR decision distinguishing primary from concurrent secondary/TFT; issue #162 and Draft PR #163 are the active test-first owner lane, have adopted current protected workflow truth non-force, and remain non-shipped while current exact-head evidence is non-terminal | employee profile, reporting and downstream authorization/graph consumers would otherwise have to guess authoritative membership from allocation/order/topology | Orgmetra #162/#163; integrate explicit category across domain/API/PostgreSQL/OpenAPI with bitemporal uniqueness, legacy provenance, semantic idempotency and no heuristic reclassification, then prove exact-head PostgreSQL/People/Foundation/Recovery/Security/SAST/review evidence | **P1 buyer truth** |
| **ASG-02 auditable assignment category correction** | issue #164 / dependent Draft #165 implement immutable predecessor closure, replacement Assignment, normalized supersession, purpose-bound HTTP/OpenAPI, audit/outbox and durable replay; correction-specific recorded time detaches accepted caller-owned timezone behavior onto a built-in fixed-offset timezone and fails closed on provider/offset integrity defects; the dedicated exact-head workflow executes the regression, but the child remains downstream of #163 with non-terminal hosted evidence | HR operations cannot safely correct a misclassified primary/secondary Assignment without either rewriting history or creating provenance ambiguity | integrate #163 first → non-force restack/retarget #165 → exact-head PostgreSQL/full-People/idempotency/security/review GREEN → atomic canonical documentation/inventory handoff → ordinary protected integration | **P1 buyer truth** |
| **UX-01 role workspaces are design truth, not shipped UI** | P1 workspaces appear in PRD/wireframes/Storybook contract; protected branch shows foundation package and design tokens but no indexed React workspace implementation | buyers cannot complete the lifecycle through a coherent UI | executable Job Architecture → Candidate Evidence → Hiring Decision → Employee Profile → Validation vertical slice; Storybook, screenshots, WCAG 2.2 AA, interaction/i18n/edge-state tests | **P1** |
| **API-01 deployable gateway/service composition** | architecture defines `orgmetra-gateway` and bounded services; protected code evidence is still foundation/package-oriented | integrations lack one deployable, supported application boundary | async-capable gateway, generated OpenAPI validation, auth/purpose/idempotency, service-owned DB access, contract/load tests | **P1** |
| **VAL-01 end-to-end validation workflow** | normalized validity/evidence architecture exists; specialist numerical ownership is correctly external | people analytics buyer cannot yet run a governed predictor→criterion→fairness workflow from UI/API | `workforce_validation` vertical slice integrating exact immutable snapshots through approved fast-mlsirm/TEPP/Psychometrics Commons boundaries; reproducibility/error evidence | **P1** |
| **OPS-01 commercial operability/SLO proof** | test/operability docs exist, but no released integrated web service proves buyer traffic characteristics | enterprise buyer lacks capacity/recovery evidence | compose deployment; Podman/Colima portability; async request handling; k6 per-page p95 ≤20 ms; recovery/backup/restore evidence; resource auto-tuning where required | **P1** |
| **SEC-02 certification-ready control evidence** | purpose-bound PII/RLS/audit contracts exist; certification is not claimed | security review still needs traceable operational evidence | NIST/SOC 2/CSAP control mapping, key management, retention/export/delete, break-glass, incident/recovery evidence; no indiscriminate PII masking | **P1** |
| **DATA-01 schema/name/persistence audit** | strong normalized temporal schema exists but every new migration/PR can introduce naming, hot-partition, lock or UPSERT drift | latent data debt can become irreversible after adoption | automated audit for at-least-two-token domain/DB identifiers where semantically required, snake_case default, 3NF ownership, per-item UPSERT/idempotency, partition/lock strategy | **P1 continuous** |
| **SCI-01 Rust scientific compute boundary** | TRD correctly reserves material mathematical/psychometric kernels for Rust; current HRIS packages are mainly governance/domain code | future analytics can regress into slow or unauditable Python numerics | every material math/psychometric/EDA/vector/matrix/token-size core is Rust or behind an explicit Rust API; CPU multithreading and justified GPU parity fixtures | **P1 continuous** |

## 9. Next product loop after P0 governance repair

The next buyer-visible vertical slice should be **Job Architecture → Candidate Evidence → Hiring Decision → Employee Profile → Validation** rather than another isolated evidence packet.

Minimum commercialization contract:

1. **Gateway** — authenticated tenant/actor/purpose context; idempotency; exact OpenAPI validation; bounded async operations; no direct peer-table reads.
2. **Job Architecture** — governed snapshot provenance, SME review, qualification rules and clear next-action states.
3. **Candidate Evidence** — purpose-bound retrieval, immutable evidence version/reference, explicit insufficiency/escalation states, no autonomous hiring decision.
4. **Hiring Decision** — human confirmation, exact sealed evidence-set digest, actor/reason/provenance, candidate-worker conversion handoff.
5. **Employee Profile** — effective/system-time assignment history and correction semantics visible without exposing internal schema names; assignment category is explicit HRIS truth rather than inferred from allocation or ordering.
6. **Validation** — exact predictor/criterion version linkage, job scope, time, subgroup/multilevel context and specialist scientific adapter evidence.
7. **UX evidence** — design tokens, Storybook scenario/edge inventory, screenshots at supported breakpoints, keyboard/touch/focus/error/degraded/permission/i18n states, exact-value alternatives for charts, WCAG 2.2 AA audit.
8. **Operability evidence** — compose-based deployment, recovery rehearsal, structured audit telemetry, k6 concurrency evidence with page p95 ≤20 ms, dependency/service failure behavior and clean close-connection handling.

This slice must use existing bounded packages instead of duplicating their domain rules in UI code.

## 10. Data, scientific and AI invariants

- Database/domain object names must be semantically explicit. `snake_case` is the default for database objects and two-or-more meaningful tokens are preferred/required where a bare one-token name such as `id` would lose domain identity; legitimate context-required `camelCase`/`PascalCase` program identifiers remain valid.
- Authoritative relational design stays in 3NF unless an explicitly measured read model is separated from the system of record.
- Tenant, bitemporal, lock/partition and item-level UPSERT/idempotency contracts are tested at the database boundary, not assumed from application code.
- Multiple assignments/memberships and time-varying context must remain modelable so person-level inference does not silently commit an atomistic fallacy.
- Psychometric/statistical weights are estimated from reviewed mathematical models; no arbitrary rule-of-thumb weighting enters production.
- Material mathematical, psychometric, EDA, vector/linear/matrix and token-size core computation is Rust-first with bounded CPU parallelism and justified GPU parity evidence.
- LLM output is draft/supporting evidence only. LLM work uses released contextual-orchestrator API/client/schema contracts; GitHub Actions request only `orchestrator/free` through the gateway token and never hard-code provider/model/group/paid fallback policy. contextual-orchestrator owns capability/price/latency/availability/accuracy discovery, supports schema-bound completions/responses and modality/embedding contracts, and preserves no-default-inference-timeout plus explicit user/provider/admin termination provenance. LLM output never receives direct authoritative employment-decision power.

## 11. Security, privacy and compliance posture

Orgmetra targets evidence readiness for CSAP/SOC 2-style enterprise review without claiming certification. PII protection must be purpose-bound and operationally usable rather than indiscriminate masking that prevents legitimate HR work. Controls include tenant/actor/purpose/resource/lifetime authorization, least privilege, forced RLS, encryption, immutable audit evidence, retention/export/delete lifecycle, incident/recovery evidence and separately governed break-glass operation.

Customer-facing language describes the user's next action and evidence state, not internal repository, schema, model or agent boundaries.

## 12. Research and standards basis

The following authoritative sources were re-checked on 2026-09-02. They define design/audit constraints; they do not by themselves certify Orgmetra or establish legal compliance. WCAG 2.2 remains the current published accessibility basis as ISO/IEC 40500:2025 while ISO/IEC has a newer revision project in development; draft work is not treated as a published requirement. NIST SP 800-53 Rev. 5 also has a finalized Release 5.2.0 control-catalog update from 2025, so current control mapping must use that release rather than assuming the original 2020 catalog is unchanged.

- International Organization for Standardization. (2023). *ISO 30405:2023 Human resource management—Guidelines on recruitment* (2nd ed.). https://www.iso.org/standard/79488.html
- International Organization for Standardization, & International Electrotechnical Commission. (2025). *ISO/IEC 40500:2025 Information technology—W3C Web Content Accessibility Guidelines (WCAG) 2.2* (2nd ed.). https://www.iso.org/standard/91029.html
- World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/
- National Institute of Standards and Technology. (2025, August 27). *NIST releases revision to SP 800-53 security and privacy controls (Release 5.2.0)*. https://csrc.nist.gov/news/2025/nist-releases-revision-to-sp-800-53-controls
- Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53 Rev. 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5
- Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall, P., & Roberts, K. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.600-1
- American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

Implementation-specific research belongs in `docs/doctoring/` and ADR/traceability records beside the exact feature it constrains. A source citation without an executable invariant/test is documentation evidence only.

## 13. Release gate

A commercial release is allowed only from one freshly fetched protected `develop` head that simultaneously proves:

- all release-scope PR dependencies are integrated in causal order;
- no unresolved valid review finding remains;
- every required exact-head deterministic gate is terminal-success, including authoritative Dependency Review rather than substitutes;
- protected-branch admission is satisfiable without synthetic approval or routine admin bypass;
- buyer vertical-slice E2E, accessibility, security, recovery and load evidence is terminal-success;
- migrations/rollback/backup-restore and tenant/purpose/audit invariants pass against production-equivalent PostgreSQL;
- documentation/ADR/TRD/API/events/schema/UI copy match the released implementation;
- release version and CHANGELOG identify the exact protected commit and migration/API compatibility; and
- no temporary self-modifying/source-fix workflow remains.

Until that evidence exists, `0.1.0` and the lack of a published release are correctly treated as pre-commercial integration state rather than a release-management defect to paper over.
