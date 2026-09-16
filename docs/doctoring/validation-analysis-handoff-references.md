# Validation-analysis handoff references

Material decisions for ADR 0027 were checked against the following primary/authoritative sources on 2026-08-21. Regulatory currency was rechecked on 2026-08-29. The #407 analysis-weight evidence boundary was checked on 2026-09-17 against the primary calibration paper, current U.S. Census methodological/quality documentation, and the current final NIST Privacy Framework. Fixed publication identifiers are retained where possible so an auditor can reproduce the cited text even when agency web pages change.

## APA 7 references

Equal Employment Opportunity Commission, Civil Service Commission, Department of Justice, & Department of Labor. (1978). *Uniform Guidelines on Employee Selection Procedures (1978)*, 43 Fed. Reg. 38,290 (August 25, 1978) (codified at 29 C.F.R. pt. 1607). The EEOC continues to list 29 C.F.R. pt. 1607 among its Title VII regulations: https://www.eeoc.gov/regulations-and-guidelines

Society for Industrial and Organizational Psychology. (2018). Principles for the validation and use of personnel selection procedures. *Industrial and Organizational Psychology, 11*(S1), 1–97. https://doi.org/10.1017/iop.2018.195

Deville, J.-C., & Särndal, C.-E. (1992). Calibration estimators in survey sampling. *Journal of the American Statistical Association, 87*(418), 376–382. https://doi.org/10.1080/01621459.1992.10475217

U.S. Census Bureau. (2021). *Statistical Quality Standard D1: Producing direct estimates from samples*. https://www.census.gov/about/policies/quality/standards/standardd1.html

U.S. Census Bureau. (2022, August 18). *Survey of Income and Program Participation: Weighting*. https://www.census.gov/programs-surveys/sipp/methodology/weighting.html

U.S. Census Bureau. (2026). *2025 Survey of Income and Program Participation users' guide* (August 2026 revision), pp. 156–157. https://www2.census.gov/programs-surveys/sipp/tech-documentation/methodology/2025_SIPP_Users_Guide.pdf

Boeckl, K., & Lefkovitz, N. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0* (NIST CSWP 01162020). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.CSWP.01162020

ContextualWisdomLab. (2026). *fast-mlsirm* (Commit 04d0bc21a2a20693bcf16108cd76d394fe844d23) [Computer software]. GitHub. https://github.com/ContextualWisdomLab/fast-mlsirm/tree/04d0bc21a2a20693bcf16108cd76d394fe844d23

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1

Office of Personnel Management. (2026). *Removal of references to the Uniform Guidelines on Employee Selection Procedures in federal personnel regulations*, 91 Fed. Reg. 48,234 (July 31, 2026) (interim final rule, RIN 3206-AP20).

## Decision notes

- 43 Fed. Reg. 38,290 and the still-listed EEOC 29 C.F.R. pt. 1607 source support keeping criterion-related validity evidence tied to an explicit study design, job relevance, accuracy, reporting, and documentation rather than treating a bare coefficient as sufficient evidence. The fixed Federal Register identifier, not a mutable `/current/` eCFR URL, is the reproducible source for the 1978 text cited by this ADR.
- The July 31, 2026 OPM interim final rule removed UGESP references from specified federal civil-service regulations. Orgmetra therefore does not present UGESP as an undifferentiated government-wide mandate; applicability must be evaluated for the employer, jurisdiction, decision, and governing law at use time.
- The SIOP Principles are the professional validation baseline used for the handoff's evidence-and-human-review posture. The journal citation above fixes volume 11, Supplement S1, pages 1–97, and DOI 10.1017/iop.2018.195.
- Deville and Särndal show that calibrated weights are produced by modifying ordinary inverse-inclusion-probability weights under explicit distance measures and calibration equations. ADR 0027 uses that narrow result to justify treating final adjusted point weights as a separately versioned scientific artifact rather than assuming `1/π_i` and calibrated weights are interchangeable. It does not mandate one calibration estimator for Orgmetra.
- Census Statistical Quality Standard D1 requires estimates and variances to account for sample design and post-sampling weighting adjustments. The SIPP methodology illustrates that final weights can combine base selection, nonresponse, longitudinal/panel, and post-stratification/calibration adjustments. These sources support provenance/reproducibility requirements only; SIPP-specific weights are not imported as Orgmetra rules.
- The August 2026 revision of the 2025 SIPP Users' Guide states that choosing a weight depends on the population to which results apply and the duration of interest, distinguishes cross-sectional monthly analysis from longitudinal multi-year analysis, and identifies explicit two-, three-, and four-year reference periods for longitudinal weights. ADR 0027 uses this only to justify fail-closed target-population/reference-duration congruence for `WeightEligibilityReceipt`; it does not adopt SIPP variable names, cohorts, or estimators as Orgmetra domain truth.
- The final NIST Privacy Framework 1.0 is used narrowly to support explicit, verifiable privacy requirements across roles in a data-processing ecosystem and life-cycle privacy-risk management. As checked on 2026-09-17, NIST's official 1.1 project page still presents Version 1.1 as an Initial Public Draft rather than a final replacement, so this ADR does not cite the draft as settled authority. The framework is voluntary and jurisdiction-agnostic; it is not employment-law permission. Orgmetra uses it only to justify carrying scientific-use purpose, released owner-contract coordinates and authorization evidence without copying sensitive auxiliary values across bounded contexts.
- The fast-mlsirm commit is recorded as a read-only dependency coordinate only. This Orgmetra slice does not modify or duplicate its numerical implementation.
- NIST AI RMF's govern, map, measure, and manage functions support preserving backend, precision, provenance, convergence, and human-review fields as inspectable result evidence rather than treating a model response as an autonomous decision.
