# Talent Management boundary references

Reference doctoring for ADR 0292, issue #292, and repair issues #294, #396, #397, #398, #399, #400, #401, #402, #403, #404, and #405. Checked against public source metadata on 2026-09-17. The ISO entries below describe scope/authority only; possession of this bibliography is not a certification or evidence that Orgmetra conforms to a paid standard's complete normative text. The legal entries constrain provenance and rights-path design only; they do not establish that a particular tenant, worker, decision, stage, or deployment is legally in scope.

## Standards and primary sources

International Organization for Standardization. (2016). *ISO 30409:2016 Human resource management—Workforce planning*. https://www.iso.org/standard/64150.html

- ISO currently lists Edition 1 as Published and Confirmed (stage 90.93), last confirmed in 2022.
- Architectural relevance: workforce planning is a distinct HR-management concern and can consume Organization/Job/People/Talent evidence without collapsing their ownership.

International Organization for Standardization. (2020). *ISO 10667-2:2020 Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers*. https://www.iso.org/standard/74717.html

- ISO currently lists Edition 2 as Published but “to be revised” (stage 90.92). Its lifecycle records systematic-review closure on 2026-03-05 and stage 90.92 on 2026-05-27.
- Architectural relevance: the published scope includes work-related assessment for promotion, succession planning, and reassignment. That supports an assessment-evidence interface for Talent workflows, not transfer of assessment or employment-decision authority into a score field.

International Organization for Standardization. (n.d.). *ISO/AWI 10667-2 Assessment service delivery—Procedures and methods to assess people in work and organizational settings—Part 2: Requirements for service providers* (Edition 3 work item). https://www.iso.org/standard/94564.html

- ISO currently lists the Edition 3 successor work item as **Under development**, stage 20.00, under ISO/TC 260.
- This AWI is evidence that revision work exists, not normative authority for an implementation or conformance claim. Until a successor edition is published, cite ISO 10667-2:2020 for current published scope and record its “to be revised” lifecycle status.
- Re-check both the 2020 edition and the Edition 3 work item before ADR acceptance, assessment-contract changes, or release/compliance claims; do not silently import draft/work-item language into Orgmetra contracts.

International Organization for Standardization. (2021). *ISO 30415:2021 Human resource management—Diversity and inclusion*. https://www.iso.org/standard/71164.html

- ISO lists Edition 1 as Published. The lifecycle shows systematic review opened on 2026-04-15 and closed on 2026-09-03 at stage 90.60; the resulting confirmation/revision disposition must be re-checked before ADR acceptance or release claims.
- The public abstract describes D&I governance, accountabilities, responsibilities, recommended actions, suggested measures, and potential outcomes, while explicitly excluding country-specific legal requirements.
- Scientific/governance relevance: stage-denominator evidence can support accountable D&I analysis, but ISO 30415 does not make `talent_management` the owner of protected attributes, fairness verdicts, or jurisdiction-specific legal conclusions.

International Organization for Standardization. (2023). *ISO 30405:2023 Human resource management—Guidelines on recruitment*. https://www.iso.org/standard/79488.html

- ISO lists Edition 2 as the current published recruitment standard.
- Architectural relevance: its recruitment-specific scope supports retaining `talent_acquisition` as the pre-hire acquisition/recruitment boundary instead of extending it by name alone into all post-hire Talent concerns.

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management—Requirements and recommendations for human capital reporting and disclosure*. https://www.iso.org/standard/30414

- Edition 2 was published in August 2025 and replaces the withdrawn 2018 edition.
- ISO's public abstract lists mobility and succession planning, workforce composition, recruitment, turnover, and skills/capabilities/development among the human-capital reporting areas.
- Architectural relevance: buyer/reporting requirements can legitimately need mobility/succession data, but reporting categories do not themselves decide which Orgmetra bounded context owns transactional truth.

International Organization for Standardization. (2025, August 24). *ISO 30414:2025—Strengthening human capital reporting and disclosure*. ISO/TC 260. https://committee.iso.org/sites/tc260/home/news/content-left-area/news-and-updates/iso-30414-2025-strengthening-hum.html

- Primary publication announcement for the second edition; useful for edition/date traceability. The standard page remains the authority for current lifecycle status.

U.S. Equal Employment Opportunity Commission. (1979). *Questions and Answers to Clarify and Provide a Common Interpretation of the Uniform Guidelines on Employee Selection Procedures*. https://www.eeoc.gov/laws/guidance/questions-and-answers-clarify-and-provide-common-interpretation-uniform-guidelines

- The EEOC page identifies this as technical assistance interpreting the 1978 Uniform Guidelines and states expressly that the document does not itself have the force and effect of law.
- It treats hiring, promotion, transfer, retention and related employment decisions as selection processes, distinguishes the total selection process from component procedures, and defines adverse impact in terms of materially different selection rates. Those rates depend on a preserved numerator and denominator rather than only on records that survive to a later stage.
- Question 47 is relevant to #400's narrower evidence-design boundary: validity evidence must correspond to the selection procedure actually used; evidence for one passing score/use does not automatically justify a substantially different passing score or ranking use.
- Scientific-design relevance: Orgmetra must retain the exact stage opportunity set and transition denominator for later `workforce_validation` analysis and identify the governing material policy regime. This is evidence-design guidance, not a universal legal-applicability declaration.

American Association for Public Opinion Research. (2026). *Disclosure Standards*. Retrieved September 17, 2026, from https://aapor.org/standards-and-ethics/disclosure-standards/

- The current public disclosure page requires enough methodological information for independent review and verification. For sampling, it asks researchers to state whether selection is probability-based or non-probability, describes probability-based selection as drawing potential participants from a known frame with known non-zero probabilities, and calls for disclosure of sampling frames and coverage gaps.
- For probability samples, it also asks reporting of sampling error and whether design effects from weighting, clustering or other factors were accounted for. Its additional-disclosure section calls for summaries of study-specific sample-record dispositions so probability-sample response rates can be computed.
- #405 uses these requirements only as reporting/provenance evidence that probability-sample status, frame/coverage, design effects and sampled-case dispositions are material to reproducibility. AAPOR survey disclosure rules are not an employment-law standard, and Orgmetra does not import AAPOR's survey vocabulary as Talent domain truth.

American Association for Public Opinion Research. (2023). *Standard definitions: Final dispositions of case codes and outcome rates for surveys* (10th ed.). https://aapor.org/standards-and-ethics/standard-definitions/

- AAPOR's current public Standard Definitions page identifies the tenth edition (2023) as the current main report and separately lists later 2025 supplements. The report's purpose is to define final case dispositions and survey outcome rates; the public page emphasizes that knowing the disposition of every element drawn in a sample is a critical first step for understanding potential nonresponse error.
- The tenth edition also covers complex designs including multistage samples, single-stage samples with unequal selection probabilities, and two-phase designs.
- #405 uses this only for the narrower design principle that a selected unit's response/nonresponse/ineligibility disposition must not disappear or become indistinguishable from a never-selected unit. Orgmetra defines its own purpose-bound Talent disposition vocabulary and leaves nonresponse adjustment and inferential consequences to `workforce_validation`.

## Engineering and provenance primary sources

Rundgren, A., Jordan, B., & Erdtman, S. (2020). *JSON Canonicalization Scheme (JCS)* (RFC 8785). RFC Editor. https://www.rfc-editor.org/rfc/rfc8785.html

- RFC 8785 is an **Informational** RFC, not an IETF Standards Track requirement. It explains why cryptographic hashing/signing needs an invariant representation so producer and consumer can repeat the same operation over semantically identical JSON.
- #399 uses this only as engineering evidence that a manifest digest needs an explicit deterministic semantic field set/representation, ordering/normalization rules, algorithm/domain/version metadata, and consumer recomputation contract. Equivalent closed manifests under the same digest contract must not acquire different identities because of serializer or presentation accidents.
- #401 uses the same narrower engineering principle for policy-regime identity. ADR 0292 does not mandate JCS, JSON, SHA-256, or any particular digest algorithm; an owner may choose another suitable canonical representation if its semantic input set, canonicalization and algorithm/domain/version are explicit and reproducible.

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation. World Wide Web Consortium. https://www.w3.org/TR/2013/REC-prov-dm-20130430/

- W3C published this Recommendation on 2013-04-30. The versioned Recommendation URI is recorded here so the cited evidence does not silently follow later W3C publication changes.
- PROV-DM models provenance through entities, activities, agents, usage and derivation relationships rather than treating an output identifier as self-explanatory.
- #401 uses PROV-DM as provenance-design evidence: a policy-regime identity retains material upstream released entities/dependencies that contributed to the selection procedure. PROV-DM does not define Orgmetra HR semantics or decide which dependency is material; that remains an owner-domain contract.

National Institute of Standards and Technology. (n.d.). *AI Risk Management Framework Playbook: MANAGE 3.1*. AI Resource Center. Retrieved September 16, 2026, from https://airc.nist.gov/airmf-resources/playbook/manage/

- MANAGE 3.1 addresses monitoring, control, and documentation of risks and benefits from third-party resources. The retrieved Playbook notes that AI systems can depend on third-party data, software, hardware, tools, services, and expertise, and recommends documenting third-party systems/components and applying risk controls.
- NIST states that the Playbook is voluntary guidance rather than a checklist that must be followed in its entirety. The site is a living resource and also notes that AI RMF 1.0 is being revised; the retrieval date above is therefore part of citation reproducibility rather than a claim that the page is immutable.
- #401 uses this as dependency-provenance/risk-management evidence only. It supports pinning material released dependencies that affect a policy regime; it does not establish validity, fairness, or legal compliance for an Orgmetra Talent procedure.
- #402 and #403 reuse the narrower dependency-governance point: a third-party or separately owned dependency needs explicit owner provenance and runtime monitoring. The Playbook does not say a cryptographic artifact digest is semantic equivalence, nor does it establish that a declared dependency is the one actually consumed during a specific Talent stage.

Supply-chain Levels for Software Artifacts. (2026). *SLSA v1.2: Provenance*. https://slsa.dev/spec/v1.2/provenance

- SLSA v1.2 is recorded as the current Approved specification on the public SLSA site as checked on 2026-09-16.
- #403 uses SLSA only as an engineering provenance analogy. It supports distinguishing declared configuration from evidence about a concrete execution; it is not an HR selection-validity, fairness, employment-law, or Orgmetra conformance authority.

Supply-chain Levels for Software Artifacts. (2026). *SLSA v1.2: Build provenance*. https://slsa.dev/spec/v1.2/build-provenance

- Build Provenance distinguishes parameters declared to the build from `resolvedDependencies`, the concrete artifacts resolved or fetched during execution. That distinction is useful by analogy for Orgmetra's intended `PolicySemanticProjection` versus trusted observed-resolved dependency evidence for one material Talent stage.
- Orgmetra does not import SLSA's build schema wholesale. The domain requirement is narrower: before an outcome can authorize a material HR stage, the trusted Talent boundary binds the terminal stage attempt to the immutable owner contracts/artifacts and material parameters actually used, compares them with the intended policy projection, and preserves any mismatch explicitly.

### Scope notes for #399, #401, #402 and #403

- #399's manifest digest is a content-identity contract over explicitly versioned closed-manifest semantics. RFC 8785 supplies only the general engineering rationale for deterministic representation; it does not select the manifest field set, serialization format, hash algorithm, or domain separator for Orgmetra.
- #401's policy-regime projection similarly uses RFC/W3C/NIST sources as engineering/provenance evidence, not HR-selection validity authority.
- #402 is an ownership/semantic-authority rule, not a demand for duplicate hashes. An upstream owner's existing canonical content digest can serve both integrity and downstream semantic identity only when the released owner contract explicitly defines the addressed canonical projection as the downstream-material semantics and publishes its stability/equivalence rules. Otherwise the owner supplies a narrower semantic projection/receipt or versioned equivalence evidence; Talent may not reconstruct foreign source truth.
- #403 is an execution-provenance rule. SLSA's declared-versus-resolved distinction and NIST's third-party-resource monitoring support the engineering need to record what was actually resolved, but neither source proves that an HR procedure is valid, fair, legally compliant, or scientifically transportable. `workforce_validation` retains those judgments.

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
- Article 14 requires effective human oversight for high-risk AI systems where applicable. In the consolidated text checked on 2026-09-10, the human overseer must, as appropriate and proportionate, understand relevant capacities and limitations, remain aware of automation bias, correctly interpret output, and be able not to use or to disregard, override, reverse, intervene in, or stop the AI system/output.
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

Horvitz, D. G., & Thompson, D. J. (1952). A generalization of sampling without replacement from a finite universe. *Journal of the American Statistical Association, 47*(260), 663–685. https://doi.org/10.1080/01621459.1952.10483446

- The paper develops finite-population estimation for sampling without replacement with unequal selection probabilities and explicitly treats inclusion probabilities as part of the estimator. The original article also discusses usefulness for the first stage of multistage designs.
- #405 uses only this foundational design-based premise: when a Talent origin is genuinely probability-sampled, inclusion-probability provenance and the design stage to which it belongs cannot be discarded if downstream analysis is expected to reproduce design-based inference.
- Scope limit: this paper does not prescribe an Orgmetra sampling design, response-disposition vocabulary, fairness metric, employment-law reporting unit, or analytic estimator. `workforce_validation` chooses the authorized estimand, weighting and variance method from the released design evidence.

Dunleavy, E. M., Mueller, L. M., Buonasera, A. K., Kuang, D. C., & Dunleavy, D. G. (2008). On the consequences of frequent applicants in adverse impact analyses: A demonstration study. *International Journal of Selection and Assessment, 16*(4), 333–344. https://doi.org/10.1111/j.1468-2389.2008.00439.x

- The demonstration study examines frequent applicants in adverse-impact analysis and shows that repeated applications by even one frequent applicant can materially create or mask statistically significant adverse-impact results under the studied conditions.
- Scientific-design relevance: a stage denominator cannot be represented only by worker identity or aggregate counts. Orgmetra must preserve an occurrence-level opportunity identity stable across retry/replay but distinct across legitimate repeated opportunities, plus an explicit counting unit. `workforce_validation` then chooses and records whether an authorized analysis estimates at opportunity/application, case, or person level.
- Scope limit: the paper demonstrates a statistical counting-unit problem; it does not prescribe Orgmetra's legal reporting unit for every tenant or jurisdiction and does not make `talent_management` the fairness-analysis owner.

Alon-Barkat, S., & Busuioc, M. (2023). Human–AI interactions in public sector decision making: “Automation bias” and “selective adherence” to algorithmic advice. *Journal of Public Administration Research and Theory, 33*(1), 153–169. https://doi.org/10.1093/jopart/muac007

- The article reports three experimental studies with an aggregate sample of 2,854 participants. It did not find a general pattern of stronger automatic adherence to algorithmic advice than equivalent human-expert advice, while it did find evidence of selective adherence to advice consistent with pre-existing stereotypes in the studied settings.
- Design relevance: “human in the loop” must not be treated as a binary compliance signal. Human–algorithm interaction can depend on context and can still be selectively biased. For Orgmetra, the appropriate control is to preserve material-stage provenance and test what evidence, alternatives, limitations, override/reversal paths, and actual human disposition existed before lock-in rather than inferring effective oversight from actor presence alone.
- Scope limit: these public-sector experiments do not validate an Orgmetra employment model, quantify employment-domain automation bias, or establish legal compliance. They support the narrower human-factors claim that actual interaction behavior and decision path matter.

Alexander, L., III, Song, Q. C., Hickman, L., & Shin, H. J. (2025). Sourcing algorithms: Rethinking fairness in hiring in the era of algorithmic recruitment. *International Journal of Selection and Assessment, 33*, e12499. https://doi.org/10.1111/ijsa.12499

- The article was first published online on 2 September 2024 and appears in the 2025 volume citation above. It models sourcing as an upstream first hurdle/prescreen that can identify or filter potential applicants before they know about the job opportunity.
- For #396, the study shows why applicant-only or survivor-only adverse-impact analysis can miss disparity introduced before a later stage, supporting stage-specific opportunity-set/transition provenance rather than only per-person decisions or final outcomes.
- For #404, the narrower design implication moves one step earlier: the **first observed cohort is not automatically the source population**. If exposure/discovery/sourcing/prescreen determines who can enter M1, later internally consistent denominator evidence remains conditional on that upstream mechanism unless its origin and coverage semantics are preserved.
- Scope limit: this is a recruitment-domain simulation/design study, not direct empirical evidence about Orgmetra succession, internal mobility, talent-pool nomination, or employee opt-in. It does not establish a universal legal protected-group denominator or require every Talent origin to be exhaustive. It supports explicit provenance that distinguishes an authoritative enumerated source universe from intentionally non-exhaustive nomination/opt-in/targeted-discovery/import origins.

Xu, H., & Zhang, N. (2024). Goal orientation for fair machine learning algorithms. *Production and Operations Management*. https://doi.org/10.1177/10591478241234998

- The paper notes that organizational-selection ML outputs are often intermediate inputs to a broader decision process rather than the final decision itself.
- Design relevance: fairness evidence must follow the decision process and its stage-specific opportunity sets instead of treating one model score or final outcome set as the whole population at risk.

### Scope notes for #404 and #405

- #404 is an opportunity-origin/coverage provenance rule, not a new fairness-analysis owner and not a universal `all employees` snapshot requirement. A purpose-bound released owner receipt can define the relevant source universe for one process/version/time; an intentionally selective origin can remain valid product behavior when it is explicit and later analysis respects that limitation.
- `talent_management` owns only the evidence needed to say how the first cohort was formed and what coverage claim may be made. Authoritative Person/Employment/Assignment/Organization/Position/Job truth remains with existing Orgmetra owners, and protected-group joins plus fairness/validity/estimand judgments remain with `workforce_validation`.
- A human or algorithmic pre-M1 exposure/discovery/nomination/prescreen is material when it changes who can enter the observed cohort. Such a step belongs in the material-stage/source-transformation provenance graph instead of disappearing merely because storage begins after it.
- #405 is conditional: it applies when the origin mechanism is genuinely probability-based. It does not require every Talent cohort to be probability sampled and does not convert nomination, opt-in, ranking, quota, convenience or deterministic-percentage selection into a probability design.
- AAPOR's disclosure and disposition material is survey-research guidance, not an Orgmetra employment-law or HR-domain standard. The useful design principle is provenance: distinguish probability from non-probability selection, preserve frame/coverage and design information, and retain what happened to selected units. Orgmetra uses its own controlled, purpose-bound Talent sampling/disposition vocabulary.
- Horvitz–Thompson is cited for the statistical need to preserve inclusion-probability information under unequal-probability finite-population sampling, not to mandate one estimator. `workforce_validation`, not Talent, owns design weights, variance/SE/CI, finite-population correction, calibration/nonresponse adjustment, inferential method, fairness/validity interpretation and any legal reporting decision.
- Sampling design can itself be sensitive. Where a stratum/cluster definition is protected or unnecessarily revealing, Talent should retain an opaque released owner/design membership reference sufficient for authorized downstream reconstruction rather than copy the underlying protected attribute or source frame.

## Evidence-handling notes

- These references constrain terminology, scope, measurement claims, provenance, human-oversight testability, first-stage opportunity-origin/source-universe coverage, probability-sampling design/disposition provenance, denominator preservation, counting-unit traceability, canonical terminal closure, manifest replacement/digest reproducibility, policy-regime compatibility, reproducible policy-semantic identity, cross-owner semantic authority, and intended-versus-actual execution provenance. They do not replace Orgmetra's protected PRD/TRD/ARCHITECTURE or an accepted owner ADR.
- ISO public abstracts are sufficient to support the scope statements recorded here, but implementation must not claim full conformance to normative requirements that have not been reviewed from licensed/current standard text.
- Re-check current ISO lifecycle/edition status when ADR 0292 is proposed for acceptance or when release/compliance documentation is produced. For ISO 10667-2, inspect both the current published 2020 edition and the active Edition 3 work item. For ISO 30415:2021, re-check the post-review disposition after the recorded 2026-09-03 close of review.
- The Korean and EU legal sources are jurisdiction- and fact-dependent. They justify a versioned decision-production, material-stage provenance, effective-oversight, and rights-response boundary; they do not establish that a particular Orgmetra decision is fully automated, high-risk, adverse, subject to Article 14/86, or otherwise legally covered.
- A compliance-policy owner must resolve then-current jurisdiction, effective dates, lawful exceptions, deadlines, and response/oversight obligations. `talent_management` consumes that released/versioned determination and preserves the evidence needed to execute it; it does not infer legal applicability from a score, model call, human name, UI event, or final decision label.
- A stage-level `fully_automated_decision` marker is process provenance, not itself a statutory classification. An upstream automated stage can remain in an AI-assisted path only if its material effect remains inspectable, reconstructable, and genuinely reversible before high-impact finalization under the Proposed product contract.
- Opportunity-set and stage-transition provenance belongs to the Talent process owner only to the extent required to reconstruct that process. Exact entry membership and counting-unit evidence must be retained without copying protected-group attributes; retry/replay attempts cannot become extra observations, and distinct legitimate repeated opportunities cannot be silently collapsed. At closure, unresolved evidence/authorization/owner availability is represented explicitly as `unavailable`, unresolved error/failure as `failed`, and `not_evaluable` remains a separate evaluability outcome; every canonical terminal class participates in the closure sum. Protected-group attributes and fairness/validity verdicts remain outside Talent and must be joined through purpose-authorized released contracts or approved analysis snapshots.
- #404 adds a boundary before that stage-denominator chain: the first persisted manifest cannot be used as its own proof of source-population completeness. A `population_complete` claim needs released/versioned owner coverage evidence; nomination, opt-in, targeted discovery, import, or other selective origin remains explicitly selective. Material pre-M1 exposure/discovery/prescreen belongs in provenance, source-enumeration failure remains visible, and `workforce_validation` must be able to distinguish source universe/origin scope from M1 and later denominators without foreign SQL or copied protected attributes.
- #405 refines the intentionally non-exhaustive branch when it is probability-based. Talent retains enough immutable design evidence to identify the authoritative source universe, sampled occurrence set, known non-zero inclusion probability or reproducible stage-wise probability inputs, design memberships/structure, actual selection execution and selected-unit dispositions. A sampled refusal/unreachable/ineligible/failure case remains different from a never-sampled unit; retries do not mint observations. Talent does not invent pseudo-probabilities for non-probability cohorts or compute analytic weights/variance from foreign source truth.
- Manifest identity is also evidence, not an opaque checksum. The owner versions the canonical semantic field set/projection, deterministic encoding/order/normalization, digest algorithm/domain separator/version and metadata contract; consumers recompute and validate it. RFC 8785 is only the engineering precedent for deterministic representation, not a mandate for Orgmetra's concrete serialization or algorithm.
- Manifest-correction provenance and policy-semantic provenance are separate. An immutable replacement lineage can resolve record corrections without establishing that a materially changed eligibility, cut-score, ranking, evidence, suppression/routing or equivalent procedure is scientifically the same procedure. Talent must expose the exact governing policy-regime/semantic identity; `workforce_validation` decides whether scientific evidence supports transport or comparison across procedures.
- #401's RFC/W3C/NIST sources are engineering/provenance evidence, not HR-selection validity standards. They support deterministic canonical representation, material upstream dependency provenance, and documented third-party-resource control. They do not decide which Talent fields are material, whether a changed procedure is valid or fair, or whether two regimes are scientifically transportable.
- #402 further limits that interpretation: an immutable artifact/version digest proves identity/integrity only to the extent its owner contract defines. Semantic compatibility across bounded contexts must come from the authoritative owner's released semantic projection/receipt or equivalence evidence; Talent must not infer it from generic digests or foreign source internals.
- #403 uses SLSA v1.2 and NIST MANAGE 3.1 only as engineering precedents for separating declared configuration from actual resolved execution and monitoring external resources. They do not establish HR-selection validity, fairness, legal applicability, or compliance. The domain contract requires trusted observed-resolved evidence because `workforce_validation` must be able to distinguish the intended procedure from the one actually executed.
- Psychometric or predictive claims require study-specific evidence. Conceptual talent-management papers, repeated-applicant demonstrations, sourcing simulations, sampling-method references, fairness-optimization research, and human–algorithm interaction studies do not establish validity, fairness, utility, or transportability of any particular Orgmetra decision rule.