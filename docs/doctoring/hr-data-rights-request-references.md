# HR Data-Rights Request References

Reviewed 2026-08-23. These sources inform a jurisdiction-neutral request-evidence boundary; they do not create a legal-compliance or certification claim.

## Current final privacy-risk framework

Boeckl, K., & Lefkovitz, N. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0* (NIST CSWP 01162020). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.CSWP.01162020

NIST describes Privacy Framework 1.0 as a voluntary, technology-, sector-, law-, and jurisdiction-agnostic privacy risk-management tool. NIST's Privacy Framework pages were rechecked on 2026-08-23: Version 1.0 remains the published final framework, while Version 1.1 remains an Initial Public Draft / forthcoming final. Orgmetra therefore does not cite the 1.1 draft as a final standard.

Primary status pages:
- https://www.nist.gov/privacy-framework/privacy-framework
- https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11

## Example statutory request categories

European Parliament & Council of the European Union. (2016). *Regulation (EU) 2016/679 of the European Parliament and of the Council of 27 April 2016 (General Data Protection Regulation)*, arts. 15–17. *Official Journal of the European Union, L 119*, 1–88. https://eur-lex.europa.eu/eli/reg/2016/679/oj

Articles 15–17 distinguish access, rectification, and erasure and attach conditions to their exercise. Orgmetra uses this only as evidence that request categories should be recorded separately from the authoritative legal/policy eligibility decision. The package does not infer GDPR applicability, data-subject status, identity authority, erasure eligibility, disclosure scope, or a fulfillment deadline from the requested action code.

## Design consequences

- Store bounded request metadata, opaque references, and SHA-256 evidence—not the HR data or free-form request body—in the durable request packet.
- Keep request intake separate from entitlement/eligibility review and from fulfillment authority.
- Re-resolve requester identity/authority, tenant, Person, applicable policy/jurisdiction, retention/legal hold, export scope, and immutable audit evidence before fulfillment.
- Treat `access_copy`, `correct_record`, `delete_record`, and `restrict_processing` as routing intents only; they are not legal conclusions.
