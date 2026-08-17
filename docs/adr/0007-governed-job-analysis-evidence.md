# ADR 0007: Governed job-analysis evidence snapshots

- Status: Accepted; persistence implementation active on PR #30
- Date: 2026-08-17
- Updated: 2026-08-18
- Owners: Orgmetra Job Architecture / Workforce Validation

## Context

Orgmetra needs a defensible job-analysis boundary before assessment design, selection validation, performance-criterion linkage, or workforce planning can rely on job requirements. A Job is not a Position or an Assignment: job-analysis evidence describes recurring work and worker requirements at the Job level, while Positions are staffable seats and Assignments bind workers to seats.

Current U.S. Office of Personnel Management guidance treats job analysis as a systematic examination of tasks, competencies, and the connection between them. OPM guidance also emphasizes job-expert input, importance or criticality evidence, current information, and documented task-to-competency linkages. The Uniform Guidelines on Employee Selection Procedures require job-analysis evidence appropriate to the validity strategy when selection procedures depend on work behaviors or job knowledge.

O*NET remains the current U.S. occupational-information system and provides occupation-level task, knowledge, skill, ability, work-activity, work-context, and related evidence. O*NET evidence does not replace local verification of the actual Job in its tenant context.

Peer-reviewed Functional Job Analysis (FJA) work demonstrates a task-based method in which subject-matter experts generate and validate task statements and certified analysts rate work content. Hysong, Best, and Moore (2007) describe ten FJA work-content dimensions: data, people, things, reasoning, mathematics, language, worker instructions, worker technology, worker interaction, and human-error consequence. Those method-specific ratings are evidence, not universal truths about a Job, and their scale anchors and sampling method must remain attributable.

LLM-generated descriptions can help analysts explore candidate language, but they are untrusted draft evidence. They must not silently become validated job requirements or high-impact employment decision evidence.

## Decision

Orgmetra will persist one immutable job-analysis version as a tenant- and Job-scoped `job_analysis_case`. Migration `0012_job_analysis_evidence_governance.sql` normalizes the evidence into:

- `source_record` and immutable `source_version`, carrying source type, locator, title, publisher, source version, retrieval/capture time, and a source-content SHA-256 digest;
- `job_analysis_source_link`, binding an exact source version and source-span reference to an analysis case;
- `task_statement`, containing observable work statements in stable sequence;
- `task_rating`, preserving dimension, value, scale bounds, rater group, and sample size instead of treating an unlabeled number as evidence;
- `fja_function` and `task_fja_link`, preserving method-versioned FJA dimensions and explicit task linkage;
- `ksao_requirement` and `task_ksao_link`, preserving Knowledge, Skill, Ability, and Other Characteristic requirements plus explicit task-to-KSAO linkage strength;
- `job_analysis_approval_record`, containing the accountable human approver, reason, evidence-version code, approval time, and a database-owned SHA-256 digest over the exact approved case content.

All persisted identities are opaque UUIDs and all relations are tenant-scoped with tenant-qualified foreign keys plus forced row-level security. The analysis case carries `effective_from`/`effective_to` business time and `recorded_at` system-record time; child evidence carries its own system-record time and inherits the case's effective scope rather than duplicating mutable business dates.

The database will not accept an approval unless the case has at least one versioned source, at least one task, importance or criticality evidence for every task, explicit FJA and KSAO linkage for every task, and a task link for every KSAO. Task↔FJA and task↔KSAO edges must resolve inside the same tenant and same analysis case.

The approval digest is computed inside PostgreSQL from deterministic, identifier-sorted canonical JSON. A caller cannot supply that digest. After approval, the case and all linked evidence are sealed: update/delete is rejected, post-approval inserts that would alter approved content are rejected, and statement-level TRUNCATE guards protect the evidence relations. Corrections require a new `analysis_version_code` and a new case rather than rewriting approved history.

`web_authoritative` sources require HTTPS locators. A source locator alone is not proof of content: the immutable `source_version` content digest, capture time, source-span reference, and approval digest preserve what exact evidence version supported the analysis. External or model-generated material remains evidence input only; the accountable human approval is the authority boundary.

This contract does not itself make hiring, promotion, termination, compensation, or other high-impact employment decisions. Later decision workflows must separately bind actor, purpose, reason, evidence version, explicit human confirmation, and immutable audit evidence.

## Consequences

### Positive

- Selection, performance, and validation work can trace requirements back to observable tasks and explicit KSAO/FJA evidence rather than free-text job descriptions.
- Current O*NET, authoritative web evidence, local SME evidence, and other governed sources can coexist without copying external service internals.
- Exact source versions, scale metadata, task links, human approval, and a database-owned approval digest make the approved analysis reconstructable and tamper-evident.
- Forced tenant isolation and same-case link checks prevent evidence from one customer or analysis version from being silently reused in another.
- LLM assistance remains reviewable draft evidence and cannot satisfy human approval on its own.

### Costs and limitations

- This persistence slice does not yet implement source ingestion, qualification-rule authoring, role-workspace UI, retention/export workflows, or selection-validity computation.
- Numeric task, FJA, and KSAO ratings are method-specific measurements. Production methods must document anchors, sampling, aggregation, reliability/inter-rater treatment, criticality rules, and local validation rationale rather than infer those properties from the numeric value alone.
- O*NET provides occupation-level evidence and does not eliminate the need to verify local Job content, context, essential requirements, and accommodations with appropriate job experts.
- Migration numbers `0010` and `0011` are owned by active PRs #26 and #28. This implementation reserves `0012` and remains Draft until those dependency lanes integrate and the exact resulting head is revalidated.

## Verification

`tests/test_job_analysis_governance_postgres.sh` is the executable PostgreSQL contract. It requires a real authoritative HTTPS source version, Task/FJA/KSAO linkage, rating provenance, database-owned approval digest, rejection of incomplete approval, post-approval sealing, cross-tenant referential rejection, update denial, TRUNCATE denial, and NOBYPASSRLS tenant isolation. `.github/workflows/job-analysis-quality.yml` is supplemental exact-head evidence and does not replace Foundation CI or organization-required workflows.

## References

The APA 7 bibliography is maintained in `docs/doctoring/REFERENCES.md`, including O*NET, current OPM Job Analysis guidance, the Uniform Guidelines on Employee Selection Procedures, SIOP's personnel-selection principles, and Hysong et al.'s peer-reviewed FJA application.
