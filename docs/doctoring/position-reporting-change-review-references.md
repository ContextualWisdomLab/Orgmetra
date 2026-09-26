# Position reporting-change review references

Verified against official primary-source pages on 2026-08-23. These references inform the governance/evidence boundary only. Orgmetra does not claim NIST certification, universal legal compliance, or conformance merely because this package uses these design principles.

## APA 7

Boeckl, K., & Lefkovitz, N. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0* (NIST CSWP 10). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.CSWP.10

Davis, K., Peabody, B., & Leach, P. (2024). *Universally unique IDentifiers (UUIDs)* (RFC 9562). RFC Editor. https://doi.org/10.17487/RFC9562

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53 Rev. 5; Release 5.2.0 supplemental control catalog current as of August 2025). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

## Applied boundary

- NIST SP 800-53 Rev. 5 AC-5 supports separation of duties. Orgmetra therefore treats requester/reviewer string inequality only as an early syntactic guard and requires authoritative actor resolution before reporting-line mutation.
- NIST SP 800-53 Rev. 5 AU-3 requires useful audit context while explicitly recognizing privacy risk in audit records. The packet therefore records organizational correlation, outcome state, reason category and timing while excluding Person identity, compensation, ratings and free-form worker narratives.
- NIST Privacy Framework 1.0 is the final framework used here for privacy-risk/minimization framing. NIST's public site currently presents Version 1.1 as non-final work; this ADR does not treat 1.1 as a final standard.
- RFC 9562 defines both UUIDv4 and UUIDv7. Orgmetra preserves the authoritative HRIS operational UUID contract, including UUIDv7, while leaf-owned change and actor correlation references use UUIDv4 to avoid silently redefining core identifier ownership.
