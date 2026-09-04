# Product and technical gap baseline

Verified: 2026-09-04 (Asia/Seoul) for Orgmetra protected/product refs. External owner-repository evidence is treated as dependency context and must be re-fetched in its canonical owner lane before mutation or release claims.

This is Orgmetra’s durable commercialization baseline, not merge authorization and not a frozen PR inventory. Volatile PR heads, workflow-run IDs, queue states, reviews, mergeability and base tips are live GitHub truth and must be fetched again before every material action.

## 1. Product thesis and buyer outcome

Orgmetra is the ContextualWisdomLab HRIS/HCM system of record for authoritative People, Organization, Position, Assignment, Job Architecture, FJA/KSAO, Talent, Assessment and Workforce truth. Its buyer value is evidence-preserving decision infrastructure: what employment fact was true, when it was true, what evidence justified a high-impact decision, who acted, what purpose authorized access, and how later outcomes validate the original job/selection model.

Primary users are HR operations owners, HRIS administrators, recruiters, hiring managers, job-analysis specialists, psychometricians/people-analytics scientists, compliance/audit reviewers, workers and enterprise integration engineers.

The buyer lifecycle is Job requirements/evidence → Candidate evidence → accountable human selection/offer → authoritative worker/employment/assignment truth → job-relevant performance evidence → validation/fairness evidence → purpose-bound operational workflows.

## 2. Truth-state contract

| State | Meaning |
| --- | --- |
| **Shipped truth** | Present on protected `develop` with executable evidence. |
| **Active PR** | Implemented only on an open exact PR head; predecessor/sibling evidence does not transfer. |
| **Accepted architecture** | Accepted ADR/PRD/TRD boundary whose implementation is incomplete. |
| **Planned** | Prioritized buyer capability without executable production evidence. |
| **Research-only** | Experiment/evidence that must not be represented as product behavior. |
| **Superseded** | Replaced decision/evidence retained for provenance only. |
| **Out of scope** | Owned by another bounded context/repository or explicitly rejected. |

A documentation-only design is never promoted to shipped truth. Merge, release, deployment and compliance claims require fresh exact-head evidence independently of this file.

## 3. Domain ownership and context map

Orgmetra owns authoritative HR domain truth. Specialist CWL systems are consumed through released/versioned contracts and ACLs; source copying, mutable-branch dependency and cross-service SQL are prohibited.

| Bounded context | Orgmetra responsibility | Integration boundary |
| --- | --- | --- |
| `people_core` | person anchors, employment, assignments, compensation references, candidate-worker linkage | Keyverse provides identity, not HRIS truth |
| `organization_core` | legal/organization units, reporting relations, locations, positions | external organization identities are referenced, not copied wholesale |
| `job_architecture` | Jobs, tasks, FJA/KSAO evidence, qualification rules, SME approval, governed snapshots | ontology/contextual-orchestrator outputs are evidence/draft adapters |
| `talent_acquisition` | requisitions, candidates, interviews, decision-evidence sets, selection/offer governance | specialist assessment systems remain evidence owners |
| `performance_management` | cycles, criterion blueprints, observations, calibration | observations bind authoritative worker/job/time scope |
| `workforce_validation` | validity-study registry, exact predictor/criterion links, subgroup/drift evidence | fast-mlsirm/TEPP/Psychometrics Commons own specialist numerical/psychometric computation |
| `document_records` | canonical document/image metadata and immutable artifact references | document services remain adapters |
| `integration_hub` | idempotency, inbox/outbox, adapter state, migration/CDC boundary | peer systems remain behind versioned ACLs |
| `audit_provenance` | append-only audit/provenance evidence | no peer service silently becomes authoritative HRIS state |

One physical PostgreSQL cluster may host multiple bounded contexts initially, but each context keeps an owned schema/role/migrations/access layer/contract. A shared physical database is not a Shared Kernel license.

## 4. Current protected truth and owner stack

Protected `develop` is `eb9757f8649aaad026a9865508d9aad50c1a7a4f`, produced by normal integration of PR #161. #161 is therefore no longer a mutable prerequisite. Its protected delta consolidates repository-owned quality workflows and pins repository runner selection to explicit `ubuntu-24.04` without weakening domain, PostgreSQL or repository validation gates.

The selector repair did not resolve the wider Actions admission incident: exact-current-head #63/#64/#65 jobs still materialize with the intended `ubuntu-24.04` label but remain queued before checkout with no runner assigned. Treat this as runner admission evidence, not as evidence that the selector repair failed and not as justification for no-op retriggers or copying workflow bytes into feature branches.

Current canonical owner order is:

1. **#63 shared HRIS-kernel audit/runtime evidence** — Draft and mechanically mergeable over current protected `develop`. A current CodeRabbit suggestion to add Job Analysis source/test files to `manifest.json` was verified against `tests/validate_repository.py` and rejected: the canonical manifest requires exact equality to its `REQUIRED` path set, which intentionally excludes those two files. Adding them would create `extra_entries` and make validation fail. The review thread was resolved without source change.
2. **#64 generic People mutation runtime integrity** — Draft and mechanically mergeable over current protected `develop`; current product/security checks remain non-terminal.
3. **#65 purpose-bound authorization plus Job Analysis durable/runtime integrity** — Draft and mechanically mergeable over current protected `develop`. Its #210 request-edge invariant is retained after #161 adoption: exact built-in Authorization text → header length at most 8,199 → Bearer parsing → token length at most 8,192. #65 must consume #63 only after #63 reaches protected truth, then reacquire exact-head evidence.
4. **#163 explicit Assignment category** — valid buyer/domain delta retained, but still based on predecessor protected truth and currently non-mergeable against current `develop`. This is a repair/restack finding, not a close condition. After #63 and applicable #64/#65 integrations, #163 must non-force adopt resulting protected truth and reacquire every exact-head gate.
5. **#165 Assignment category correction/supersession** — Draft child of #163. Preserve its close → replacement → predecessor/replacement provenance delta until #163 integrates, then non-force restack/adopt protected truth and rerun all exact-head gates.

Protected `develop` still does not make explicit primary-vs-concurrent-secondary Assignment classification shipped truth. Allocation, row order, Position identity and graph topology are not classification authority.

There are no published Orgmetra GitHub releases as of this verification. Do not manufacture a release merely to clear the count.

## 5. Effective GitHub governance

Orgmetra’s effective default-branch control plane is inherited organization ruleset **18156473 — `CWL Central required workflows`**, active as of 2026-09-04. Current live parameters are:

- one approving review required;
- stale reviews dismissed after push;
- review-thread resolution required;
- extra approval required for unattributed changes;
- merge and squash are the allowed merge methods;
- deletion and non-fast-forward protection are enabled;
- required workflows are `opencode-review`, `pr-review-merge-scheduler`, `security-scan`, `strix`, `sast-semgrep`, `noema-review`, and `codeql-pr`;
- `OrganizationAdmin/always` bypass is exposed.

Routine bypass, self-approval, synthetic reviewer identity, gate weakening or treating model/bot review as the required human approval are not acceptable repair strategies. Central ruleset mutation remains owned by `ContextualWisdomLab/.github`; Orgmetra records the dependency and canary evidence but does not create a leaf workflow shim or copy central policy source.

## 6. Commercialization gap register

| Gap | Current evidence | Buyer consequence | Owner / next acceptance evidence | Priority |
| --- | --- | --- | --- | --- |
| **GOV-01 satisfiable protected admission** | inherited ruleset still requires one approval and exposes routine admin bypass | otherwise-GREEN work may be unable to progress normally, while bypass weakens auditability | canonical `.github` owner repair → live ruleset convergence → unchanged Orgmetra canary through ordinary path | **P0** |
| **RUN-01 Actions runner admission** | #161 selector/workflow consolidation is protected truth; current #63/#64/#65 jobs carry `ubuntu-24.04` yet remain pre-checkout with no runner | exact-head product/security evidence remains unavailable | central/repository Actions admission RCA; unchanged candidate must materially execute rather than no-op retrigger | **P0 evidence** |
| **SEC-01 authoritative Dependency Review** | required central workflow remains owner-controlled; substitutes cannot prove dependency diff | merge evidence can be incomplete or misleading | immutable released central workflow + authenticated exact comparison + material pinned action execution | **P0** |
| **REL-01 integrated release evidence** | no published release and no single integrated protected head proves the full buyer/security/operability gate set | buyers cannot install/deploy a supported release | causal owner integration → protected-head release checklist → version/CHANGELOG/tag/package/SBOM/provenance/reproducibility/rollback | **P0** |
| **AUTH-01 purpose-bound authorization/durable trust boundary** | #65 retains exact tenant/resource/purpose/operation/scope/field narrowing, exact runtime validation, decision revalidation, durable Job Analysis integrity and #210 request budget; still Active PR | remote/request/plugin-controlled data must not become HR policy authority or executable evidence before validation | #63 protected integration → #65 non-force protected adoption → exact-head product/PostgreSQL/security/review evidence → normal integration | **P1 security foundation** |
| **ASG-01 explicit Assignment authority** | #162/#163 retain explicit `primary | concurrent_secondary`; `legacy_unspecified` is historical/restoration provenance; #163 is currently behind/conflicting with current protected truth | employee profile/reporting/authorization/graph consumers otherwise have to guess authoritative membership | integrate #63/#64/#65 as applicable → non-force adopt protected truth into #163 → PostgreSQL/API/OpenAPI/idempotency/bitemporal evidence → ordinary integration | **P1 buyer truth** |
| **ASG-02 auditable Assignment correction** | #164/#165 retain immutable predecessor closure, replacement and normalized supersession provenance | HR operations cannot safely correct misclassification without rewriting history or losing provenance | #163 protected integration → #165 non-force restack/adoption → exact-head People/PostgreSQL/idempotency/security/review evidence → ordinary integration | **P1 buyer truth** |
| **UX-01 role workspaces** | PRD/wireframe/design foundations exist; buyer-facing executable workspace evidence is not yet sufficient for a release claim | buyer lifecycle is not yet proven end-to-end through a coherent UI | Job Architecture → Candidate Evidence → Hiring Decision → Employee Profile → Validation vertical slice; Storybook/current-head E2E/a11y/i18n/edge-state evidence | **P1** |
| **API-01 deployable gateway/composition** | service/package contracts exist but no released integrated application boundary is available | integrations lack one supported deployment contract | async gateway, generated OpenAPI validation, purpose/idempotency, service-owned persistence, contract/load/recovery tests | **P1** |
| **VAL-01 governed validation workflow** | normalized validity/evidence architecture exists and scientific compute ownership remains external | people-analytics buyer cannot yet run the complete predictor→criterion→fairness workflow | exact immutable snapshots through released fast-mlsirm/TEPP/Psychometrics Commons contracts; reproducibility/error evidence | **P1** |
| **OPS-01 commercial operability/SLO** | operability/test contracts exist; no released integrated web service proves buyer traffic/recovery characteristics | enterprise buyer lacks capacity/recovery evidence | Podman/Colima → compose/k8s path, async handling, clean connection lifecycle, recovery rehearsal, k6 buyer-path p95 ≤20 ms | **P1** |
| **SEC-02 certification-ready control evidence** | purpose-bound PII/RLS/audit architecture exists; certification is not claimed | security review still requires operational control evidence | NIST/SOC 2/CSAP mapping, key/retention/export/delete/break-glass/incident/recovery evidence | **P1** |
| **DATA-01 schema/persistence audit** | strong bitemporal/tenant foundations exist; every new migration can still introduce naming, lock, hot-partition or idempotency drift | latent data debt becomes expensive after adoption | automated naming/3NF/ownership/UPSERT/idempotency/partition-lock audit | **P1 continuous** |
| **SCI-01 Rust scientific compute boundary** | HRIS domain code is not itself a reason to move into Rust; material math/psychometrics/EDA kernels remain Rust-first by architecture | future analytics could regress into slow or unauditable numerics | Rust API for material kernels, bounded CPU parallelism, justified GPU parity and true-parameter recovery evidence | **P1 continuous** |

## 7. Next buyer-visible product loop

After P0 governance/execution prerequisites are materially runnable, the next commercial slice should be **Job Architecture → Candidate Evidence → Hiring Decision → Employee Profile → Validation**, not another isolated evidence packet.

Minimum acceptance:

1. authenticated tenant/actor/purpose context, idempotency and exact OpenAPI validation at the gateway;
2. governed Job snapshot provenance, SME review and qualification rules;
3. immutable Candidate Evidence references with insufficiency/escalation states and no autonomous hiring decision;
4. human-confirmed Hiring Decision bound to an exact sealed evidence set and candidate-worker conversion;
5. bitemporal Employee Profile with explicit Assignment category and correction provenance;
6. Validation with exact predictor/criterion versions, Job scope, time and subgroup/multilevel context;
7. material UI evidence for normal/loading/empty/error/permission/responsive/keyboard/touch/focus/i18n states in KO/EN/JA/ZH/VI/ES/DE/FR, including CJK/text expansion/font fallback;
8. operability/recovery/load evidence against production-equivalent PostgreSQL and real buyer paths rather than reduced samples or unrealistic warm-cache exclusions.

UI work must use reusable objects/page composition and product design evidence rather than template filler. Keyverse remains identity backend; authentication journey remains product form. Translation resources are versioned DB resources with screen-key cache and remain separate from ontology-label truth.

## 8. Data, scientific and AI invariants

- DDD subdomains, bounded contexts, UL, aggregates, entities, value objects, domain services, repositories, events and invariants must agree across code/API/DB/tests.
- Relational authoritative truth remains normalized; read models are separated explicitly when measured need justifies them.
- Tenant, bitemporal, lock/partition and item-level UPSERT/idempotency contracts are tested at database boundaries.
- Multiple assignments/memberships and time-varying context remain representable; person-level inference must not silently commit atomistic fallacy.
- Material mathematical/psychometric/EDA/vector/linear/matrix/token-size computation is Rust-first with bounded CPU parallelism and justified GPU parity.
- Psychometric acceptance uses true-parameter recovery, RMSE, bias, coverage and reproducibility. Synthetic data is unit-test evidence, not real-world acceptance.
- LLM output is draft/supporting evidence only. LLM work consumes released contextual-orchestrator API/client/schema contracts; GitHub Actions request only `orchestrator/free` through the gateway token and do not hard-code provider/model/group/paid fallback policy. Capability absence fails closed and is repaired in the canonical orchestrator owner.

## 9. Security, privacy and compliance posture

Orgmetra targets evidence readiness for CSAP/SOC 2-style enterprise review without claiming certification. PII controls are purpose-bound and operationally usable: tenant/actor/purpose/resource/lifetime authorization, least privilege, forced RLS where applicable, encryption, immutable audit evidence, retention/export/delete lifecycle, incident/recovery evidence and separately governed break-glass operation.

Customer-facing language describes the user’s next action and evidence state, not internal repository/schema/model/agent boundaries.

## 10. Research and standards basis

These sources define design/audit constraints; they do not certify Orgmetra or establish legal compliance by citation alone. Implementation-specific citations and invariants belong in `docs/doctoring/`, ADRs and traceability records beside the code/test they constrain.

- International Organization for Standardization. (2023). *ISO 30405:2023 Human resource management—Guidelines on recruitment* (2nd ed.). https://www.iso.org/standard/79488.html
- International Organization for Standardization, & International Electrotechnical Commission. (2025). *ISO/IEC 40500:2025 Information technology—W3C Web Content Accessibility Guidelines (WCAG) 2.2* (2nd ed.). https://www.iso.org/standard/91029.html
- World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https://www.w3.org/TR/WCAG22/
- Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53 Rev. 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5
- National Institute of Standards and Technology. (2025, August 27). *NIST releases revision to SP 800-53 security and privacy controls (Release 5.2.0)*. https://csrc.nist.gov/news/2025/nist-releases-revision-to-sp-800-53-controls
- Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall, P., & Roberts, K. (2024). *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile* (NIST AI 600-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.600-1
- American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

A source citation without an executable invariant/test is documentation evidence only.

## 11. Release gate

A commercial release is allowed only from one freshly fetched protected `develop` head that simultaneously proves:

- release-scope dependencies integrated in causal order;
- no unresolved valid review finding;
- every required exact-head deterministic gate terminal-success, including authoritative Dependency Review rather than substitutes;
- satisfiable protected-branch admission without synthetic approval or routine admin bypass;
- buyer vertical-slice E2E, accessibility, security, recovery and load evidence terminal-success;
- migrations/rollback/backup-restore and tenant/purpose/audit invariants against production-equivalent PostgreSQL;
- documentation/ADR/TRD/API/events/schema/UI copy matching released implementation;
- release version and CHANGELOG bound to the exact protected commit and migration/API compatibility;
- immutable package/release plus SBOM/provenance/reproducibility/rollback evidence; and
- no temporary purpose-complete self-modifying/source-fix workflow.

Until this evidence exists, version `0.1.0` and zero published releases are correctly treated as pre-commercial integration state rather than a release-management defect to paper over.