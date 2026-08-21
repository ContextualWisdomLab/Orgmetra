# Validation-analysis handoff references

Material decisions for ADR 0027 were checked against the following primary/authoritative sources on 2026-08-21.

## APA 7 references

Electronic Code of Federal Regulations. (2026). *29 C.F.R. pt. 1607—Uniform Guidelines on Employee Selection Procedures (1978).* Retrieved August 21, 2026, from https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.). Cambridge University Press. https://www.apa.org/ed/accreditation/personnel-selection-procedures.pdf

ContextualWisdomLab. (2026). *fast-mlsirm* (Commit 04d0bc21a2a20693bcf16108cd76d394fe844d23) [Computer software]. GitHub. https://github.com/ContextualWisdomLab/fast-mlsirm/tree/04d0bc21a2a20693bcf16108cd76d394fe844d23

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1

## Decision notes

- 29 C.F.R. §§ 1607.5 and 1607.14 support keeping criterion-related validity evidence tied to an explicit study design, job relevance, accuracy, reporting, and documentation rather than treating a bare coefficient as sufficient evidence.
- The SIOP Principles are the professional validation baseline used for the handoff's evidence-and-human-review posture.
- The fast-mlsirm commit is recorded as a read-only dependency coordinate only. This Orgmetra slice does not modify or duplicate its numerical implementation.
- NIST AI RMF's govern, map, measure, and manage functions support preserving backend, precision, provenance, convergence, and human-review fields as inspectable result evidence rather than treating a model response as an autonomous decision.
