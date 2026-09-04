# HR Access Review — Primary References

Verified against current NIST public materials on **2026-08-23 (Asia/Seoul)**. The normative publication reviewed is NIST SP 800-53 Rev. 5; NIST's Cybersecurity and Privacy Reference Tool currently lists the finalized control-catalog dataset as **SP 800-53 Rev. 5.2.0**. These sources are engineering inputs, not evidence that Orgmetra or a buyer is certified or compliant with a particular framework.

## References (APA 7)

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Rev. 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2025, August 27). *NIST releases revision to SP 800-53 security and privacy controls*. Computer Security Resource Center. https://csrc.nist.gov/News/2025/nist-releases-revision-to-sp-800-53-controls

National Institute of Standards and Technology. (2026). *Cybersecurity and Privacy Reference Tool: Catalog*. Computer Security Resource Center. https://csrc.nist.gov/projects/cprt/catalog

## Design consequences used by this PR

- **AC-2 Account Management:** account compliance review uses an organization-defined frequency. Orgmetra therefore records bounded review evidence but does not invent a universal annual, quarterly, or monthly cadence.
- **AC-5 Separation of Duties:** reviewer/requester/subject separation is represented directly so a reviewer cannot also be the requester or reviewed subject within this packet.
- **AC-6 Least Privilege:** recommendations can retain, reduce, or remove **existing** access only. There is deliberately no recommendation that expands or grants access.
- A recommendation is not enforcement authority. Current identity, tenant, purpose, resource scope, policy and entitlement state must be re-resolved before a separate access mutation can occur.

NIST finalized Release 5.2.0 in August 2025 and publishes it through CPRT. This PR relies on the stable Rev. 5 AC-2/AC-5/AC-6 semantics used by the access-review contract and records the currently published catalog release separately so a minor dataset label cannot silently masquerade as the normative publication identity.
