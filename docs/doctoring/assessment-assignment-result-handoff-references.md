# Assessment assignment coordination and result-handoff references

This note supports Proposed ADR 0429. It records the authority used to separate **Orgmetra HR-side assessment coordination** from **Psychometrics Commons assessment operations / immutable result ownership** and from downstream validity/fairness authority. It does not certify an assessment provider, instrument, scoring model, cutoff, legal conclusion, or deployment.

## Repository ownership authority reviewed 2026-09-21

Protected Orgmetra authority is internally consistent on the specialist boundary:

- `CLAUDE.md`: Psychometrics Commons owns assessment operations and immutable assessment result snapshots.
- Repository README: Psychometrics Commons + fast-mlsirm own the assessment lifecycle and psychometric computation boundary.
- Accepted ADR 0001: Psychometrics Commons, fast-mlsirm and TEPP remain specialist boundaries for assessment operations, numerical kernels and temporal analysis artifacts; Orgmetra stores references to those artifacts.
- Accepted ADR 0002: sibling CWL products remain behind explicit package/API/event/adapter contracts and product ownership does not transfer merely because a protocol is consumed.
- Protected TRD: assessment results stay external immutable snapshot references unless a later ADR transfers instrument lifecycle ownership.

Psychometrics Commons protected README independently states that it owns product APIs, instrument publication, participant/session lifecycle, response events, scoring dispatch, immutable result snapshots, product persistence and resource authorization. Therefore an Orgmetra-local `AssessmentAdministration`/session or result-snapshot lifecycle would duplicate existing protected owner truth.

At this review the Psychometrics Commons GitHub release inventory is empty. Protected-main or an immutable commit is useful design evidence but, under the CWL integration/release rule applied to this work, is not a production contract for Orgmetra. ADR 0429 therefore treats an immutable released owner contract as a hard prerequisite for executable integration.

## Current standards status reviewed 2026-09-21

International Organization for Standardization. (2020a). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 1: Requirements for the client* (ISO 10667-1:2020). https://www.iso.org/standard/74716.html

ISO 10667-1:2020 is the published client-side edition. Its public scope covers the client's needs/rationale, conditions of use, assessment approach, access/use/storage of results, and organizational decisions. Its examples include recruitment, selection, development, appraisal, promotion, succession planning, and reassignment. This supports Orgmetra owning the HR-side reason/purpose/assignment and accountable use of assessment evidence across more than recruitment. It does **not** require the client HRIS to own the assessment service provider's session or scoring runtime.

International Organization for Standardization. (2020b). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (ISO 10667-2:2020). https://www.iso.org/standard/74717.html

ISO 10667-2:2020 remains the published service-provider counterpart. Its public scope includes selection/implementation/evaluation of assessment procedures, interpretation/reporting, personal and assessment data, competence/professionalism, and organizational decisions. ADR 0429 uses the Part 1 / Part 2 split to preserve a client-side HR coordination contract while leaving the service-provider assessment operation behind the specialist boundary. A result callback is never treated as proof of provider compliance or scientific adequacy.

International Organization for Standardization. (2026a). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 1: Requirements for the client* (ISO/AWI 10667-1, Edition 3, work item). https://www.iso.org/standard/94563.html

International Organization for Standardization. (2026b). *Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (ISO/AWI 10667-2, Edition 3, work item). https://www.iso.org/standard/94564.html

Both Edition 3 work items were registered on 2026-05-27 and remain under development at stage 20.00 at this review. They are change-watch evidence only. ADR 0429 must be rechecked when either replacement reaches publication or exposes a material requirement that changes the client/provider boundary.

## Professional standards and guidance

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*. American Educational Research Association.

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.). Author.

Society for Industrial and Organizational Psychology. (2023). *Considerations and recommendations for the validation and use of AI-based assessments for employee selection*. https://www.siop.org/post/siop-releases-recommendations-for-ai-based-assessments/

The SIOP AI-assessment recommendations emphasize job-related score meaning, score consistency, fairness, appropriate operational use, and documentation of development/scoring steps for verification and audit. ADR 0429 uses those principles to require an exact released procedure/instrument/scoring/result coordinate and explicit intended use. They do not transfer scoring or assessment-session ownership into Orgmetra. Scientific adequacy remains a Workforce Validation responsibility.

## Peer-reviewed evidence

Berry, C. M., Lievens, F., Zhang, C., & Sackett, P. R. (2024). Insights from an updated personnel selection meta-analytic matrix: Revisiting general mental ability tests' role in the validity–diversity trade-off. *Journal of Applied Psychology, 109*(10), 1611–1634. https://doi.org/10.1037/apl0001203

*Correction to “Insights from an updated personnel selection meta-analytic matrix: Revisiting general mental ability tests' role in the validity-diversity trade-off” by Berry et al. (2024).* (2025). *Journal of Applied Psychology, 110*(9), 1239. https://doi.org/10.1037/apl0001308

The 2025 erratum corrects adverse-impact ratios for the dotted lines in Figure 1 of Berry et al. (2024). It states that the error does not change the article's conclusions. Any future Orgmetra use of numerical adverse-impact ratios from that figure must therefore use the corrected figure/erratum rather than the original Figure 1 values.

Merritt, S. M., & Ryan, A. M. (2024). Gendered competencies and gender composition: A human versus algorithm evaluator comparison. *International Journal of Selection and Assessment, 32*(2), 225–248. https://doi.org/10.1111/ijsa.12459

Sackett, P. R., Zhang, C., Berry, C. M., & Lievens, F. (2022). Revisiting meta-analytic estimates of validity in personnel selection: Addressing systematic overcorrection for restriction of range. *Journal of Applied Psychology, 107*(11), 2040–2068. https://doi.org/10.1037/apl0000994

These papers reinforce that assessment interpretation depends on the procedure, scoring/use context, criterion and sampling/selection conditions. They do not justify a universal assessment score, cutoff, validity coefficient, diversity conclusion, or automated employment decision.

## Architectural interpretation

The combined repository, standards and research evidence supports five narrow decisions in ADR 0429:

1. Orgmetra needs cross-lifecycle **HR assignment/purpose/correlation truth**, so that business fact should not be hidden as generic connector transport or forced into a recruitment-only context.
2. Psychometrics Commons remains the owner of assessment session/administration, response, scoring-dispatch, immutable result-snapshot and specialist supersession lifecycles; Orgmetra stores only released references/bindings.
3. A production result handoff requires an immutable released owner contract. A protected-main SHA, PR SHA, source copy or digest-only reference is not the cross-repository production contract.
4. Orgmetra needs exact purpose plus exact released execution/result/scoring provenance to support accountable downstream consumption, but callback success or score presence grants no selection, validity or fairness authority.
5. Selection/Talent and Workforce Validation must independently authorize and reconstruct the exact Orgmetra assignment and exact specialist evidence they consume.

Any future implementation must doctor new jurisdiction-specific legal requirements separately. These professional/measurement sources are not a substitute for legal advice or tenant-specific compliance policy.