# ADR 0001: Orgmetra owns authoritative HRIS records

## Status

Status: Accepted

## Context

Orgmetra must become a full HRIS/HCM platform, not merely a resume screening tool. Buyers and operators cannot reconstruct who was employed, in which job and seat, under which decision, or with which later outcome if those facts live only in an ATS, an assessment vendor, or a document store.

ISO 30400:2022 is the published human-resource vocabulary for the ISO HR management family. It exists so terms such as workforce, employment, and human capital keep a shared meaning across products and reports. Orgmetra adopts that vocabulary for employment-truth records; it does not treat a specialist product's local labels as the system of record.

ISO 30414:2025 is the current published human-capital reporting and disclosure standard. It includes workforce composition among the core reporting areas. The 2018 edition is withdrawn and is not the current catalog record. Reconstructable composition counts require durable people, employment, organization, job, position, and assignment facts. A resume parser or scoring service cannot satisfy that reporting need.

Selection validity also requires post-hire records. The Uniform Guidelines on Employee Selection Procedures (29 C.F.R. Part 1607, 1978) treat criterion-related evidence as a relationship between a selection procedure and later work outcomes. SIOP (2018) states the same professional requirement: validation and use of personnel selection procedures depend on job-related criteria and later performance or other outcome evidence. Those studies cannot be assembled unless Orgmetra already owns the employment, assignment, criterion, observation, decision, and validity-study linkage records.

Psychometrics Commons, fast-mlsirm, and TEPP remain specialist boundaries for assessment operations, numerical kernels, and temporal analysis artifacts. Orgmetra stores references to those artifacts. It does not reimplement their engines, and it does not let model output become an autonomous high-impact employment decision.

## Decision

Orgmetra owns the authoritative record for people, employment, organization, jobs, positions, assignments, candidate-worker linkage, performance criteria, criterion observations, compensation, employment transitions, selection decisions, and validity studies.

Person, employment, organization, job, position, and assignment remain separate concepts. A person is not an employment. An employment is not a seat. A job definition is not a filled assignment. Candidate evidence becomes worker-linked only through an append-only hire linkage; it does not replace the employment record.

External CWL services may provide identity, communication, assessment snapshots, ontology, document rendering, migration, or analysis artifacts through published contracts. They do not own employment truth. Keyverse remains the identity leaf. Orgmetra remains the employment-truth leaf.

High-impact selection, hire, promotion, compensation, and similar decisions stay human-accountable. Orgmetra records the decision, the sealed evidence set, and later outcomes so an operator can approve, review, correct, request evidence, compare, export, or escalate. LLM output may enter only as draft evidence.

## Consequences

- Operators can reconstruct workforce composition and later validity cases from Orgmetra-owned facts instead of stitching vendor extracts.
- External services may provide evidence, identity, assessment snapshots, document rendering, or analysis artifacts.
- External services do not own employment truth and must not be copied into Orgmetra as substitute tables.
- Selection and reporting work can request post-hire evidence, compare a decision to later criterion observations, and export a reconstructable case file.
- Orgmetra must provide strong audit, retention, and purpose-bound access so necessary HR fields stay usable for authorized work.
- Psychometric computation and identity issuance stay outside this ownership boundary; missing specialist artifacts are referenced, not re-created.

## References

The APA 7th bibliography is maintained in `docs/doctoring/REFERENCES.md`. This ADR uses:

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures*. 29 C.F.R. Part 1607. https://www.govinfo.gov/content/pkg/CFR-2025-title29-vol4/pdf/CFR-2025-title29-vol4-part1607.pdf

International Organization for Standardization. (2022). *ISO 30400:2022 Human resource management — Vocabulary*. ISO. https://www.iso.org/standard/78044.html

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO. https://www.iso.org/standard/30414

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.). SIOP. https://doi.org/10.1017/iop.2018.195
