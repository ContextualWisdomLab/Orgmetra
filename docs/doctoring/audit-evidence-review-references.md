# Audit evidence review references

Reviewed 2026-08-24 against current authoritative sources.

## References (APA 7)

Cloud Native Computing Foundation. (2022). *CloudEvents specification (Version 1.0.2)*. https://github.com/cloudevents/spec/tree/v1.0.2

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations (NIST Special Publication 800-53, Revision 5; updated release catalog 5.2.0)*. National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

## Design use

CloudEvents v1.0.2 remains the latest stable CloudEvents core release reviewed for the existing Orgmetra audit envelope. The package therefore rechecks `specversion = 1.0` and the existing JSON media-type contract rather than adopting a working draft.

NIST SP 800-53 Rev. 5 AU-6 identifies audit-record review, analysis and reporting as an organizational control capability. Orgmetra uses that as a design input for purpose-bound reviewability and accountable access. The reference does not imply NIST certification, FedRAMP authorization, SOC 2 attestation, or that this bounded package implements the entire AU family.
