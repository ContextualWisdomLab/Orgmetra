# Product Requirements Document: Orgmetra

## 1. Product vision

Orgmetra is an evidence-centered HRIS and HCM platform whose temporal HRIS core connects jobs, people, selection decisions, work opportunities, performance outcomes, and validation evidence across the full employment lifecycle.

## 2. Problem

Current HR systems often separate job architecture, recruiting, assessment, employee records, performance management, compensation, and people analytics. This separation prevents organizations from answering high-stakes questions:

- What work did this job actually require at the time of selection?
- Which evidence justified the hiring or promotion decision?
- Did selection evidence predict later job performance?
- Did performance criteria actually measure the job analysis model?
- Did organizational context, manager, opportunity, or time distort the observed outcome?
- Can HR act on PII without unsafe masking while remaining compliant and auditable?

## 3. Target users

- HR operations owner
- HRIS administrator
- recruiter
- hiring manager
- job-analysis specialist
- psychometrician / people analytics scientist
- compliance / audit reviewer
- employee / worker
- enterprise integration engineer

## 4. Jobs to be done

1. Define a job profile from web evidence, internal documents, task analysis, FJA, KSAO, SME review, and versioned approval.
2. Link a candidate's evidence to job requirements without reducing them to keywords.
3. Record human selection decisions with explicit evidence, uncertainty, and constraints.
4. Convert a hired candidate into a worker without losing candidate evidence provenance.
5. Track assignments and performance outcomes over effective time and system time.
6. Validate whether selection tools predict job-relevant outcomes and whether they do so fairly.
7. Integrate specialist CWL services without destroying the HRIS source-of-truth boundary.

## 5. Scope

### P0 foundation

- People, employment, organization, job, position, assignment models.
- Bitemporal effective/system time for HR facts.
- Candidate-worker linkage.
- Performance cycle, criterion blueprint, and criterion observation models.
- Selection decision records.
- Validity study registry.
- Audit/provenance contract.
- CWL integration adapter contracts.
- Documentation and diagram baseline.

### P1 product slice

- Job Architecture workspace.
- Candidate Evidence workspace.
- Hiring decision record.
- Employee profile with bitemporal assignment history.
- Validation dashboard shell.

The checkout also contains a local fixture slice at `apps/hr-workspace/` for
HR Home and Employee Profile, with a local Storybook runtime for its tokenized
states. It is an interaction and accessibility contract for the protected
People API boundary, not a connected or deployed customer workflow until its
API and browser E2E evidence are merged and released.

### P2 scale

- HRIS migration pipelines.
- Psychometrics Commons integration.
- TEPP longitudinal analysis integration.
- Semantic Data Portal occupation ontology integration.
- Naruon communication scheduling integration.

## 6. Non-goals

- Orgmetra is not an autonomous hiring bot.
- Orgmetra is not the identity provider; Keyverse owns that boundary.
- Orgmetra is not the psychometric numerical kernel; fast-mlsirm owns that boundary.
- Orgmetra is not the mailbox or calendar provider; Naruon and customer providers own that boundary.
- Orgmetra does not directly query other products' application tables.

## 7. Functional requirements

| ID | Requirement |
|---|---|
| FR-001 | The system shall store person, employment, organization, job, position, and assignment as distinct records. |
| FR-002 | The system shall store effective time and system-recorded time for HR facts. |
| FR-003 | The system shall link candidates to workers append-only after hiring. |
| FR-004 | The system shall store job analysis versions, task inventories, FJA profiles, KSAO profiles, and qualification rules. |
| FR-005 | The system shall store selection decisions with evidence references and decision actor. |
| FR-006 | The system shall store effective-dated performance cycles, criterion blueprints, and criterion observations linked to exactly one cycle. |
| FR-007 | The system shall register validation studies and link them to predictors, criteria, samples, and decision policy versions. |
| FR-008 | The system shall support purpose-bound access rather than global PII masking. |
| FR-009 | The system shall integrate CWL services only through versioned APIs, events, packages, or adapters. |
| FR-010 | The system shall distinguish shipped truth, active PR, accepted architecture, planned, research-only, superseded, and out-of-scope states in documentation. |

## 8. Non-functional requirements

- Auditability: every high-impact decision links to evidence and actor context.
- Reliability: idempotent commands and explicit retry/compensation where integrations fail.
- Security: least privilege, tenant isolation, field-level authorization, encryption, retention, and export control.
- Compliance readiness: CSAP and SOC 2 evidence readiness without certification claims.
- Accessibility: WCAG 2.2 AA-oriented UI with exact-value tables for charts.
- Scientific integrity: psychometric claims require validity evidence, not correlation-only shortcuts.

## 9. Success metrics

- Time to create a reviewable job profile from evidence.
- Percentage of hiring decisions with complete evidence lineage.
- Percentage of candidate-worker links with preserved provenance.
- Criterion blueprint coverage by job family.
- Criterion observations assigned to a valid effective-dated performance cycle.
- Validity studies with predictor/criterion version linkage.
- Access decisions with purpose, actor, and resource evidence.
- Migration records reconciled without untraceable rows.
