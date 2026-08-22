# HR Access Review — Primary References

Checked against current NIST public materials on 2026-08-23. These sources are engineering inputs, not evidence that Orgmetra or a buyer is certified or compliant with a particular framework.

## References (APA 7)

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Rev. 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2026). *SP 800-53 controls downloads*. Computer Security Resource Center. https://csrc.nist.gov/projects/risk-management/sp800-53-controls/downloads

## Design consequences used by this PR

- **AC-2 Account Management:** account compliance review uses an organization-defined frequency. Orgmetra therefore records bounded review evidence but does not invent a universal annual, quarterly, or monthly cadence.
- **AC-5 Separation of Duties:** reviewer/requester/subject separation is represented directly so a reviewer cannot also be the requester or reviewed subject within this packet.
- **AC-6 Least Privilege:** recommendations can retain, reduce, or remove **existing** access only. There is deliberately no recommendation that expands or grants access.
- A recommendation is not enforcement authority. Current identity, tenant, purpose, resource scope, policy and entitlement state must be re-resolved before a separate access mutation can occur.

NIST's current download page identifies SP 800-53 Rev. 5 as the authoritative control source and publishes current release data. This PR cites the stable Revision 5 control semantics rather than depending on a minor-release label for the packet contract.
