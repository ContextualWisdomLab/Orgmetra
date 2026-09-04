# HR data export control — research and standards record

Status: active-PR supporting evidence. Checked against authoritative primary sources on 2026-08-22. This file does not claim certification or legal compliance.

## Decision-relevant evidence

NIST Privacy Framework 1.0 remains the current final Privacy Framework baseline: NIST's current Privacy Framework page still identifies Version 1.0 as the final framework while Version 1.1 remains an Initial Public Draft / forthcoming update. The export-review slice therefore cites 1.0 as normative final guidance and treats 1.1 only as non-normative research input.

NIST SP 800-162 defines attribute-based access control in terms of subject, object, requested operation, and relevant environmental attributes evaluated against policy. Orgmetra applies that principle by treating an export purpose as one narrowing attribute, never as blanket permission to disclose HR fields.

NIST SP 800-53 Rev. 5 (including published updates) integrates security and privacy control families including Access Control, Audit and Accountability, and PII Processing and Transparency. The slice uses those control objectives as design evidence for least privilege, explicit field scope, accountable human review, value-minimized audit evidence, and separation between review and actual egress.

## Architecture consequence

The package intentionally emits only pre-export governance metadata and leaves the export state `not_authorized_to_export`. Actual protected values remain behind the authoritative Orgmetra People boundary until current tenant/resource/purpose/field authorization and human approval are re-resolved and auditable. This is an engineering control boundary, not a statement that every jurisdiction's portability, disclosure, retention, or labor-law obligation is implemented.

## APA 7 references

Hu, V. C., Ferraiolo, D., Kuhn, R., Schnitzer, A., Sandlin, K., Miller, R., & Scarfone, K. (2019). *Guide to attribute based access control (ABAC) definition and considerations* (NIST Special Publication 800-162, updated August 2, 2019). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-162

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5, including updates as of December 10, 2020). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0* (NIST Cybersecurity White Paper 10). https://doi.org/10.6028/NIST.CSWP.10

## Primary-source URLs checked

- https://www.nist.gov/privacy-framework
- https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11
- https://csrc.nist.gov/pubs/cswp/10/nist-privacy-framework-version-10/final
- https://csrc.nist.gov/pubs/sp/800/162/upd2/final
- https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
