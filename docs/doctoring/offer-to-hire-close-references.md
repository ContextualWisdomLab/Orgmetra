# Offer-to-hire close references

Reviewed 2026-08-24. These sources inform the governance principle that a candidate response and prior selection evidence remain evidence inputs to an accountable employer decision process; they do not turn candidate acknowledgement, an assessment score, or an automated signal into employment authority by themselves.

## Primary / authoritative sources

U.S. Equal Employment Opportunity Commission. (2007, December 1). *Employment tests and selection procedures*. https://www.eeoc.gov/laws/guidance/employment-tests-and-selection-procedures

- The EEOC identifies employment tests and other selection procedures as subject to federal anti-discrimination law and directs employers to ensure that selection procedures are properly validated for the positions and purposes for which they are used.
- Orgmetra therefore preserves the existing accountable selection-decision authorization boundary rather than allowing an offer-response packet to bypass it.

U.S. Equal Employment Opportunity Commission. (n.d.). *Regulations and guidelines*. Retrieved August 24, 2026, from https://www.eeoc.gov/regulations-and-guidelines

- The current EEOC regulations index identifies 29 C.F.R. Part 1607 as the Uniform Guidelines on Employee Selection Procedures.
- This repository treats the Uniform Guidelines as a governing selection-procedure reference, not as a software certification claim.

Society for Industrial and Organizational Psychology. (2023, January 21). *Considerations and recommendations for the validation and use of AI-based assessments for employee selection*. https://www.siop.org/wp-content/uploads/legacy/SIOP%20Considerations%20and%20Recommendations%20for%20the%20Validation%20and%20Use%20of%20AI-Based%20Assessments%20for%20Employee%20Selection%20010323.pdf

- SIOP states that AI-based assessments used for hiring and promotion should meet the same scrutiny and standards applied to traditional employment tests and emphasizes documentation for verification and auditing.
- #108 does not introduce an AI decision path. The reference supports the broader Orgmetra rule that evidence provenance and accountable human/employer authority remain distinct from any evidence-generating mechanism.

## Repository interpretation

The cited materials do not prescribe Orgmetra's exact API shape. The software contract is an engineering control derived from the product's high-impact-decision requirements: candidate acceptance is necessary evidence for closing an accepted offer, while the authoritative candidate/offer/selection mapping, purpose-bound authorization, and immutable HR mutation remain separate controlled boundaries.
