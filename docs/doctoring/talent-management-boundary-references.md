# Talent Management boundary references

Reference doctoring for ADR 0292 and issue #292. Checked against public source metadata on 2026-09-10. The ISO entries below describe scope/authority only; possession of this bibliography is not a certification or evidence that Orgmetra conforms to a paid standard's complete normative text.

## Standards and primary sources

International Organization for Standardization. (2016). *ISO 30409:2016 Human resource management—Workforce planning*. https://www.iso.org/standard/64150.html

- ISO currently lists Edition 1 as Published and Confirmed (stage 90.93), last confirmed in 2022.
- Architectural relevance: workforce planning is a distinct HR-management concern and can consume Organization/Job/People/Talent evidence without collapsing their ownership.

International Organization for Standardization. (2020). *ISO 10667-2:2020 Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers*. https://www.iso.org/standard/74717.html

- ISO currently lists Edition 2 as Published but “to be revised” (stage 90.92). Its lifecycle records systematic-review closure on 2026-03-05 and stage 90.92 on 2026-05-27.
- Architectural relevance: the published scope includes work-related assessment for promotion, succession planning, and reassignment. That supports an assessment-evidence interface for Talent workflows, not transfer of assessment or employment-decision authority into a score field.

International Organization for Standardization. (n.d.). *ISO/AWI 10667-2 Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (Edition 3 work item). https://www.iso.org/standard/94564.html

- ISO currently lists the Edition 3 successor work item as **Under development**, stage 20.00 (new project registered in the TC/SC work programme), under ISO/TC 260.
- Traceability rule: this AWI is evidence that revision work exists, not normative authority for an implementation or conformance claim. Until a successor edition is published, cite ISO 10667-2:2020 for current published scope and record its “to be revised” lifecycle status.
- Re-check both the 2020 edition and the Edition 3 work item before ADR acceptance, assessment-contract changes, or release/compliance claims; do not silently import draft/work-item language into Orgmetra contracts.

International Organization for Standardization. (2023). *ISO 30405:2023 Human resource management—Guidelines on recruitment*. https://www.iso.org/standard/79488.html

- ISO lists Edition 2 as the current published recruitment standard.
- Architectural relevance: its recruitment-specific scope supports retaining `talent_acquisition` as the pre-hire acquisition/recruitment boundary instead of extending it by name alone into all post-hire Talent concerns.

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management—Requirements and recommendations for human capital reporting and disclosure*. https://www.iso.org/standard/30414

- Edition 2 was published in August 2025 and replaces the withdrawn 2018 edition.
- ISO's public abstract lists mobility and succession planning, workforce composition, recruitment, turnover, and skills/capabilities/development among the human-capital reporting areas.
- Architectural relevance: buyer/reporting requirements can legitimately need mobility/succession data, but reporting categories do not themselves decide which Orgmetra bounded context owns transactional truth.

International Organization for Standardization. (2025, August 24). *ISO 30414:2025—Strengthening human capital reporting and disclosure*. ISO/TC 260. https://committee.iso.org/sites/tc260/home/news/content-left-area/news-and-updates/iso-30414-2025-strengthening-hum.html

- Primary publication announcement for the second edition; useful for edition/date traceability. The standard page remains the authority for current lifecycle status.

## Peer-reviewed conceptual and scientific sources

Collings, D. G., & Mellahi, K. (2009). Strategic talent management: A review and research agenda. *Human Resource Management Review, 19*(4), 304–313. https://doi.org/10.1016/j.hrmr.2009.04.001

- Relevance: identifies persistent conceptual-boundary problems in talent management and frames strategic talent management around pivotal positions, talent pools, differentiated HR architecture, and organizational outcomes. ADR implication: model pivotal Position/Job references and talent-pool decisions explicitly rather than placing an undifferentiated `talent` property on Person.

Dries, N. (2013). The psychology of talent management: A review and research agenda. *Human Resource Management Review, 23*(4), 272–285. https://doi.org/10.1016/j.hrmr.2013.05.001

- Relevance: synthesizes multiple psychological perspectives and tensions in the talent construct, including inclusive/exclusive, innate/acquired, input/output, and transferable/context-dependent views. ADR implication: no universal potential/readiness score becomes domain truth without an explicit construct and decision-use definition.

Gallardo-Gallardo, E., Dries, N., & González-Cruz, T. F. (2013). What is the meaning of “talent” in the world of work? *Human Resource Management Review, 23*(4), 290–300. https://doi.org/10.1016/j.hrmr.2013.05.002

- Relevance: distinguishes “talent as characteristics” from “talent as people” and inclusive from exclusive approaches. ADR implication: `TalentPoolMembership` is an organizational planning relation, not proof that an individual possesses a timeless latent trait called talent.

## Evidence-handling notes

- These references constrain terminology, scope, measurement claims, and interfaces. They do not replace Orgmetra's protected PRD/TRD/ARCHITECTURE or an accepted owner ADR.
- ISO public abstracts are sufficient to support the scope statements recorded here, but implementation must not claim full conformance to normative requirements that have not been reviewed from licensed/current standard text.
- Re-check current ISO lifecycle/edition status when ADR 0292 is proposed for acceptance or when release/compliance documentation is produced. For ISO 10667-2, inspect both the current published 2020 edition and the active Edition 3 work item.
- Psychometric or predictive claims require study-specific evidence. Conceptual talent-management papers do not establish validity, fairness, utility, or transportability of any particular Orgmetra decision rule.
