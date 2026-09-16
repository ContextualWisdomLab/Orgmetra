# Validation-analysis handoff references

Material decisions for ADR 0027 were checked against the following primary/authoritative sources on 2026-08-21. Regulatory currency was rechecked on 2026-08-29; fixed publication identifiers are retained so an auditor can reproduce the cited text even when agency web pages change.

## APA 7 references

Equal Employment Opportunity Commission, Civil Service Commission, Department of Justice, & Department of Labor. (1978). *Uniform Guidelines on Employee Selection Procedures (1978)*, 43 Fed. Reg. 38,290 (August 25, 1978) (codified at 29 C.F.R. pt. 1607). The EEOC continues to list 29 C.F.R. pt. 1607 among its Title VII regulations: https://www.eeoc.gov/regulations-and-guidelines

Society for Industrial and Organizational Psychology. (2018). Principles for the validation and use of personnel selection procedures. *Industrial and Organizational Psychology, 11*(S1), 1–97. https://doi.org/10.1017/iop.2018.195

ContextualWisdomLab. (2026). *fast-mlsirm* (Commit 04d0bc21a2a20693bcf16108cd76d394fe844d23) [Computer software]. GitHub. https://github.com/ContextualWisdomLab/fast-mlsirm/tree/04d0bc21a2a20693bcf16108cd76d394fe844d23

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1

Office of Personnel Management. (2026). *Removal of references to the Uniform Guidelines on Employee Selection Procedures in federal personnel regulations*, 91 Fed. Reg. 48,234 (July 31, 2026) (interim final rule, RIN 3206-AP20).

## Decision notes

- 43 Fed. Reg. 38,290 and the still-listed EEOC 29 C.F.R. pt. 1607 source support keeping criterion-related validity evidence tied to an explicit study design, job relevance, accuracy, reporting, and documentation rather than treating a bare coefficient as sufficient evidence. The fixed Federal Register identifier, not a mutable `/current/` eCFR URL, is the reproducible source for the 1978 text cited by this ADR.
- The July 31, 2026 OPM interim final rule removed UGESP references from specified federal civil-service regulations. Orgmetra therefore does not present UGESP as an undifferentiated government-wide mandate; applicability must be evaluated for the employer, jurisdiction, decision, and governing law at use time.
- The SIOP Principles are the professional validation baseline used for the handoff's evidence-and-human-review posture. The journal citation above fixes volume 11, Supplement S1, pages 1–97, and DOI 10.1017/iop.2018.195.
- The fast-mlsirm commit is recorded as a read-only dependency coordinate only. This Orgmetra slice does not modify or duplicate its numerical implementation.
- NIST AI RMF's govern, map, measure, and manage functions support preserving backend, precision, provenance, convergence, and human-review fields as inspectable result evidence rather than treating a model response as an autonomous decision.
