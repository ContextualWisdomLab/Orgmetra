# Talent Management boundary references

Reference doctoring for ADR 0292, issue #292, and repair issue #294. Checked against public source metadata on 2026-09-10. The ISO entries below describe scope/authority only; possession of this bibliography is not a certification or evidence that Orgmetra conforms to a paid standard's complete normative text. The legal entries constrain provenance and rights-path design only; they do not establish that a particular tenant, worker, decision, stage, or deployment is legally in scope.

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

## Privacy and AI decision-rights primary sources

대한민국. (2025). *개인정보 보호법* [시행 2025. 10. 2.; 법률 제20897호, 2025. 4. 1., 일부개정]. 국가법령정보센터. https://www.law.go.kr/법령/개인정보보호법

- Article 37-2 is conditional, not a blanket rule for every algorithm-assisted employment workflow. It addresses decisions made by a **fully automated system** that significantly affect a data subject's rights or obligations, subject to the statute's stated exceptions and conditions.
- The provision gives qualifying data subjects a refusal right and an explanation-request path; absent a justified refusal ground, the controller must take measures such as not applying the automated decision, human intervention/reprocessing, or explanation as required by the provision.
- Architectural relevance: Orgmetra must preserve how the outcome was actually produced. A human actor ID, confirmation click, or later label is not sufficient provenance to determine whether a decision was fully automated or meaningfully human-decided.
- Applicability remains a legal/policy determination based on the then-current decision, tenant, jurisdiction, lawful basis, and statutory conditions. ADR 0292 does not declare all Talent decisions subject to Article 37-2.

대한민국. (2026). *개인정보 보호법 시행령* [시행 2026. 8. 20.; 대통령령 제36121호, 2026. 2. 19.]. 국가법령정보센터. https://www.law.go.kr/법령/개인정보보호법시행령

- Articles 44-2 through 44-4 operationalize automated-decision requests and transparency. The current decree includes an explanation request concerning criteria/process and review of whether additional information or an opinion can be reflected, and requires public disclosure of specified automated-decision information and request methods.
- Architectural relevance: explanation/review is a product workflow with versioned decision-policy evidence and response provenance, not merely a static privacy-policy link. The rights response must still protect other workers' restricted evidence.

개인정보보호위원회. (2024). *자동화된 결정에 대한 개인정보처리자의 조치 기준* (개인정보보호위원회고시 제2024-9호, 2024. 9. 26., 제정). 국가법령정보센터. https://law.go.kr/admRulLsInfoP.do?admRulSeq=2100000247380

- Effective 2024-09-26. The notice supplies operational criteria for refusal/explanation requests, including response handling and justified-refusal treatment.
- Architectural relevance: time limits, refusal grounds, and response contents belong in a versioned compliance-policy contract. The current values are evidence for implementation and testing, not timeless constants in the Talent domain model.
- Re-check the notice and its legal basis before implementation/release because an administrative rule can be amended independently of the Talent aggregate contract.

European Parliament & Council of the European Union. (2024). *Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)*. Official Journal of the European Union. https://eur-lex.europa.eu/eli/reg/2024/1689/oj

- Annex III point 4 covers specified employment and worker-management uses, including recruitment/selection and AI systems intended to make decisions affecting terms of work-related relationships, promotion/termination, task allocation, and monitoring/evaluation where the regulation's high-risk conditions are met.
- Article 86 provides, for the decisions within its scope, a right to a clear and meaningful explanation of the AI system's role in the decision-making procedure and the main elements of the decision taken.
- Article 14 requires effective human oversight for high-risk AI systems where applicable. In the consolidated text current on 2026-09-10, the human overseer must, as appropriate and proportionate, understand relevant capacities and limitations, remain aware of automation bias, correctly interpret output, and be able not to use or to disregard, override, reverse, intervene in, or stop the AI system/output.
- Architectural relevance: a reviewer name or confirmation event is not evidence that oversight was effective. If an automated eligibility, exclusion, ranking, suppression, threshold, or routing stage materially constrains the reachable outcome, Orgmetra must preserve that stage and make any claimed human intervention operationally testable before lock-in.
- This is design/traceability evidence only. Article 14 applicability depends on the then-current legal classification, system, deployment, role, dates, and facts; ADR 0292 does not turn the Article 14 list into a universal Talent-domain legal rule.

European Parliament & Council of the European Union. (2026). *Consolidated text of Regulation (EU) 2024/1689 as of 27 July 2026*. EUR-Lex. https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02024R1689-20260727

- This consolidated text was re-checked for #294 because it contains the current Article 14 wording after the 2026 amendments. It is preferred over relying on the original 2024 text alone when evaluating current human-oversight wording.
- Traceability relevance: Article 14(4) explicitly addresses automation-bias awareness and practical ability, where appropriate and proportionate, to interpret, disregard, override, reverse, intervene in, or stop AI output. The ADR uses those concepts to define testable oversight properties without declaring every Talent workflow legally covered.

European Parliament & Council of the European Union. (2026). *Regulation (EU) 2026/1744 of 8 July 2026 amending Regulations (EU) 2024/1689, (EU) 2018/1139 and (EU) 2023/1230 as regards the simplification of the implementation of harmonised rules on artificial intelligence (Digital Omnibus on AI).* Official Journal of the European Union, L 2026/1744. https://eur-lex.europa.eu/eli/reg/2026/1744/oj

- The amendment is in force and changes the staged application of the AI Act. The consolidated timing must be checked rather than relying on the original 2024 dates; as of this doctoring pass, the relevant Annex III Chapter III Sections 1–3 high-risk regime has a later application date under the 2026 amendment.
- Architectural relevance: application dates and transitional conditions are versioned legal-policy evidence. Do not encode the currently observed date as an immutable Talent invariant, and do not claim present EU high-risk compliance merely because ADR 0292 preserves explanation or oversight provenance.
- Before ADR acceptance or a European production release, re-read the then-current consolidated Regulation (EU) 2024/1689 and Regulation (EU) 2026/1744 rather than copying this summary into a compliance claim.

## Peer-reviewed conceptual and scientific sources

Collings, D. G., & Mellahi, K. (2009). Strategic talent management: A review and research agenda. *Human Resource Management Review, 19*(4), 304–313. https://doi.org/10.1016/j.hrmr.2009.04.001

- Relevance: identifies persistent conceptual-boundary problems in talent management and frames strategic talent management around pivotal positions, talent pools, differentiated HR architecture, and organizational outcomes. ADR implication: model pivotal Position/Job references and talent-pool decisions explicitly rather than placing an undifferentiated `talent` property on Person.

Dries, N. (2013). The psychology of talent management: A review and research agenda. *Human Resource Management Review, 23*(4), 272–285. https://doi.org/10.1016/j.hrmr.2013.05.001

- Relevance: synthesizes multiple psychological perspectives and tensions in the talent construct, including inclusive/exclusive, innate/acquired, input/output, and transferable/context-dependent views. ADR implication: no universal potential/readiness score becomes domain truth without an explicit construct and decision-use definition.

Gallardo-Gallardo, E., Dries, N., & González-Cruz, T. F. (2013). What is the meaning of “talent” in the world of work? *Human Resource Management Review, 23*(4), 290–300. https://doi.org/10.1016/j.hrmr.2013.05.002

- Relevance: distinguishes “talent as characteristics” from “talent as people” and inclusive from exclusive approaches. ADR implication: `TalentPoolMembership` is an organizational planning relation, not proof that an individual possesses a timeless latent trait called talent.

Alon-Barkat, S., & Busuioc, M. (2023). Human–AI interactions in public sector decision making: “Automation bias” and “selective adherence” to algorithmic advice. *Journal of Public Administration Research and Theory, 33*(1), 153–169. https://doi.org/10.1093/jopart/muac007

- The article reports three experimental studies with an aggregate sample of 2,854 participants. It did not find a general pattern of stronger automatic adherence to algorithmic advice than equivalent human-expert advice, while it did find evidence of selective adherence to advice consistent with pre-existing stereotypes in the studied settings.
- Design relevance: “human in the loop” must not be treated as a binary compliance signal. Human–algorithm interaction can depend on context and can still be selectively biased. For Orgmetra, the appropriate control is to preserve material-stage provenance and test what evidence, alternatives, limitations, override/reversal paths, and actual human disposition existed before lock-in rather than inferring effective oversight from actor presence alone.
- Scope limit: these public-sector experiments do not validate an Orgmetra employment model, quantify employment-domain automation bias, or establish legal compliance. They support the narrower human-factors claim that actual interaction behavior and decision path matter.

## Evidence-handling notes

- These references constrain terminology, scope, measurement claims, provenance, human-oversight testability, and interfaces. They do not replace Orgmetra's protected PRD/TRD/ARCHITECTURE or an accepted owner ADR.
- ISO public abstracts are sufficient to support the scope statements recorded here, but implementation must not claim full conformance to normative requirements that have not been reviewed from licensed/current standard text.
- Re-check current ISO lifecycle/edition status when ADR 0292 is proposed for acceptance or when release/compliance documentation is produced. For ISO 10667-2, inspect both the current published 2020 edition and the active Edition 3 work item.
- The Korean and EU legal sources are jurisdiction- and fact-dependent. They justify a versioned decision-production, material-stage provenance, effective-oversight, and rights-response boundary; they do not establish that a particular Orgmetra decision is fully automated, high-risk, adverse, subject to Article 14/86, or otherwise legally covered.
- A compliance-policy owner must resolve then-current jurisdiction, effective dates, lawful exceptions, deadlines, and response/oversight obligations. `talent_management` consumes that released/versioned determination and preserves the evidence needed to execute it; it does not infer legal applicability from a score, model call, human name, UI event, or final decision label.
- A stage-level `fully_automated_decision` marker is process provenance, not itself a statutory classification. An upstream automated stage can remain in an AI-assisted path only if its material effect remains inspectable, reconstructable, and genuinely reversible before high-impact finalization under the Proposed product contract.
- Psychometric or predictive claims require study-specific evidence. Conceptual talent-management papers and human–algorithm interaction studies do not establish validity, fairness, utility, or transportability of any particular Orgmetra decision rule.