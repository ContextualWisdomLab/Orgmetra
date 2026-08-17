# ADR 0007: Governed job-analysis evidence snapshots

- Status: Accepted on stacked implementation branch
- Date: 2026-08-17
- Owners: Orgmetra Job Analysis / Workforce Validation

## Context

Orgmetra needs a defensible Job analysis boundary before assessment design, selection validation, performance-criterion linkage, or workforce planning can rely on job requirements. A Job is not a Position or an Assignment: job-analysis evidence describes recurring work and worker requirements at the Job level, while Positions are staffable seats and Assignments bind workers to seats.

Current U.S. Office of Personnel Management guidance treats job analysis as a systematic examination of the tasks performed in a job, the competencies required to perform those tasks, and the connection between tasks and competencies. OPM also emphasizes job-expert input, importance ratings, current evidence, and documented task-to-competency linkages. The Uniform Guidelines on Employee Selection Procedures likewise require job-analysis evidence appropriate to the validity strategy when selection procedures depend on work behaviors or job knowledge.

O*NET is the current U.S. occupational-information system; production release 30.3 was published in May 2026 and exposes task, knowledge, skill, ability, work-activity, and related occupational data. The older Dictionary of Occupational Titles was last updated in 1991 and has been replaced by O*NET. Its Data/People/Things worker-function codes remain useful only as an explicitly historical Functional Job Analysis compatibility vocabulary.

LLM-generated descriptions can help analysts explore candidate language, but they are not authoritative evidence and must not silently become validated job requirements or high-impact employment decision evidence.

## Decision

Orgmetra will represent one version of Job analysis evidence with an immutable `JobAnalysisSnapshot` containing:

- tenant and Job identity plus analysis identity, version, effective date, and recorded instant;
- observable `TaskEvidence` with importance and difficulty ratings;
- `KSAORequirement` records for knowledge, skill, ability, and other-characteristic requirements with importance and proficiency ratings;
- explicit `TaskKSAOLink` records with relationship strength and essential-task indication;
- one `FunctionalJobAnalysisProfile` carrying historical DOT Data/People/Things worker-function codes only as a compatibility descriptor;
- provenance for every task, KSAO, and FJA item through an `EvidenceSource` with HTTPS source URI, source title/version, retrieval instant, source-content SHA-256 digest, and controlled origin code;
- an optional accountable human reviewer reference and review instant.

The snapshot is tenant- and Job-scoped. Validated snapshots require complete Task-to-KSAO coverage, accountable human review, and non-LLM evidence. Any `llm_draft` source forces the material to remain `analysis_draft`. Draft evidence can be preserved for analyst review but cannot be represented as validated evidence.

Canonical snapshot JSON sorts Tasks, KSAOs, and their link records by opaque durable identifiers. `content_digest()` is SHA-256 over those exact UTF-8 canonical bytes so downstream validity studies can bind to an exact version without copying mutable prose into unrelated systems.

This contract does not make hiring, promotion, termination, compensation, or other high-impact employment decisions. Later decision workflows must separately bind actor, purpose, reason, evidence version, human confirmation, and immutable audit evidence.

## Consequences

### Positive

- Selection and assessment work can trace requirements back to observable work and explicit KSAO linkages rather than free-text job descriptions.
- Current O*NET evidence and local SME evidence can coexist with explicit source/version/digest provenance.
- Historical FJA codes remain interoperable without being mistaken for current occupational data.
- LLM assistance remains reviewable draft evidence and cannot satisfy validated-analysis requirements.
- Stable canonical bytes make later validity-study and criterion evidence reproducible and attributable to one exact Job analysis version.

### Costs and limitations

- This slice is a pure domain/evidence contract; persistence, SME workflow, source ingestion, authorization, retention/export controls, UI, and selection-validity computation remain separate owner boundaries.
- The 1–5 rating scales are contract-level normalized ordinals. A production job-analysis method must document its sampling, anchors, aggregation, criticality rules, inter-rater treatment, and local validation rationale rather than infer those properties from the ordinal values alone.
- O*NET provides occupation-level evidence and does not eliminate the need to verify local Job content, context, and essential requirements with appropriate job experts.

## Verification

The contract requires realistic tests for tenant/Job isolation, unique durable identities, non-dangling and complete Task-KSAO links, controlled KSAO categories, valid FJA ranges, evidence provenance, deterministic canonicalization, review timing, reserved UUID rejection, LLM draft-only governance, and exact 100% owned production statement/branch coverage where the pinned toolchain exposes those metrics.

## References

The APA 7 bibliography is maintained in `docs/doctoring/REFERENCES.md`, including O*NET 30.3, current OPM Job Analysis guidance, the Uniform Guidelines on Employee Selection Procedures, SIOP's personnel-selection principles, and the archived 1991 DOT Appendix B worker-function vocabulary.
