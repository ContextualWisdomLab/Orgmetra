# Doctoring — HR document retrieval references

This note records primary public standards used as design evidence for the active HR document retrieval PR. It does not claim certification, regulatory compliance, or legal entitlement to disclose any particular employee document.

## Design implications

- **NIST Privacy Framework 1.0** is the current final NIST Privacy Framework baseline used by this design. It motivates explicit data-processing purpose, data minimization, privacy-risk management, and controlled data processing. NIST is separately developing Privacy Framework 1.1; current NIST material identifies that work as an Initial Public Draft, so this ADR does not treat 1.1 as a final standard.
- **NIST SP 800-53 Rev. 5 / Release 5.2.0** supplies current security/privacy control vocabulary relevant to access control, Audit and Accountability, PII Processing and Transparency, and System and Information Integrity. The package uses those families as design evidence for deny-by-default exact-scope authorization, immutable audit-before-release, minimized receipts, and content-integrity verification.
- These sources are risk/control references rather than proof that an Orgmetra deployment conforms to NIST, SOC 2, CSAP, or any legal regime. Deployment-specific policy, identity assurance, retention/legal-hold rules, storage protections, and audit durability remain separately testable responsibilities.

## APA 7 references

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0* (NIST CSWP 10). U.S. Department of Commerce. https://doi.org/10.6028/NIST.CSWP.01162020

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5; current control catalog Release 5.2.0). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

## Verification notes

Primary NIST pages were rechecked on 2026-08-25. NIST's Privacy Framework page identifies Version 1.0 and separately advertises the Privacy Framework 1.1 Initial Public Draft. The NIST SP 800-53 page identifies Rev. 5 as final and links the current Release 5.2.0 supplemental/control-catalog update.
