# Assessment assignment and result-handoff references

This note supports ADR 0429. It records the authority used to separate Orgmetra assessment-delivery orchestration from external instrument/scoring ownership and from downstream validity/fairness authority. It does not certify an assessment provider, instrument, scoring model, cutoff, legal conclusion, or deployment.

## Current standards status reviewed 2026-09-21

International Organization for Standardization. (2020a). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 1: Requirements for the client* (ISO 10667-1:2020). https://www.iso.org/standard/74716.html

ISO 10667-1:2020 is the published client-side edition. Its public scope covers the client's needs/rationale, conditions of use, assessment approach, access/use/storage of results, and organizational decisions. Its examples include recruitment, selection, development, appraisal, promotion, succession planning, and reassignment. This is the strongest standards basis for treating assessment assignment/use as a business lifecycle rather than generic connector state.

International Organization for Standardization. (2020b). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (ISO 10667-2:2020). https://www.iso.org/standard/74717.html

ISO 10667-2:2020 remains the published service-provider counterpart. Its public scope includes selection/implementation/evaluation of assessment procedures, interpretation/reporting, personal and assessment data, competence/professionalism, and organizational decisions. ADR 0429 uses it to require explicit released provider/procedure/scoring provenance; Orgmetra does not infer provider compliance from a result callback.

International Organization for Standardization. (2026a). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 1: Requirements for the client* (ISO/AWI 10667-1, Edition 3, work item). https://www.iso.org/standard/94563.html

International Organization for Standardization. (2026b). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (ISO/AWI 10667-2, Edition 3, work item). https://www.iso.org/standard/94564.html

Both Edition 3 work items were registered on 2026-05-27 and remain under development at stage 20.00 at this review. They are change-watch evidence only. ADR 0429 must be rechecked when either replacement reaches publication or exposes a material requirement that changes the client/provider boundary.

## Professional standards and guidance

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.). Author.

Society for Industrial and Organizational Psychology. (2023). *Considerations and recommendations for the validation and use of AI-based assessments for employee selection*. https://www.siop.org/post/siop-releases-recommendations-for-ai-based-assessments/

The SIOP AI-assessment recommendations explicitly emphasize job-related score meaning, score consistency, fairness, appropriate operational use, and documentation of development/scoring steps for verification and audit. ADR 0429 uses those principles only to justify immutable procedure/scoring/version/use provenance and fail-closed `not_verifiable` behavior. Scientific adequacy remains a Workforce Validation responsibility.

## Peer-reviewed evidence

Berry, C. M., Lievens, F., Zhang, C., & Sackett, P. R. (2024). Insights from an updated personnel selection meta-analytic matrix: Revisiting general mental ability tests' role in the validity–diversity trade-off. *Journal of Applied Psychology, 109*(10), 1611–1634. https://doi.org/10.1037/apl0001203

*Correction to “Insights from an updated personnel selection meta-analytic matrix: Revisiting general mental ability tests' role in the validity-diversity trade-off” by Berry et al. (2024).* (2025). *Journal of Applied Psychology, 110*(9), 1239. https://doi.org/10.1037/apl0001308

The 2025 erratum corrects adverse-impact ratios for the dotted lines in Figure 1 of Berry et al. (2024). It states that the error does not change the article's conclusions. Any future Orgmetra use of numerical adverse-impact ratios from that figure must therefore use the corrected figure/erratum rather than the original Figure 1 values.

Merritt, S. M., & Ryan, A. M. (2024). Gendered competencies and gender composition: A human versus algorithm evaluator comparison. *International Journal of Selection and Assessment, 32*(2), 225–248. https://doi.org/10.1111/ijsa.12459

Sackett, P. R., Zhang, C., Berry, C. M., & Lievens, F. (2022). Revisiting meta-analytic estimates of validity in personnel selection: Addressing systematic overcorrection for restriction of range. *Journal of Applied Psychology, 107*(11), 2040–2068. https://doi.org/10.1037/apl0000994

These papers reinforce that assessment interpretation depends on the procedure, scoring/use context, criterion and sampling/selection conditions. They do not justify a universal assessment score, cutoff, validity coefficient, diversity conclusion, or automated employment decision.

## Architectural interpretation

The reference set supports four narrow decisions in ADR 0429:

1. assessment use is cross-lifecycle business state, so it should not be hidden as generic integration transport;
2. Orgmetra needs exact purpose, procedure/scoring contract version, administration occurrence, result-owner locator and correction provenance to support accountable consumption;
3. operational assessment delivery does not imply ownership of instrument content, item/response data, scoring algorithms, or psychometric conclusions; and
4. downstream selection and Workforce Validation must independently authorize and reconstruct the exact evidence they consume.

Any future implementation must doctor new jurisdiction-specific legal requirements separately. These professional/measurement sources are not a substitute for legal advice or tenant-specific compliance policy.