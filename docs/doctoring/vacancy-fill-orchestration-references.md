# Vacancy fill orchestration references

Reviewed 2026-08-24.

## Primary standards

National Institute of Standards and Technology. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2026). *SP 800-53 Rev. 5 controls: Current version 5.1*. Computer Security Resource Center. https://csrc.nist.gov/projects/risk-management/sp800-53-controls/downloads

## Applied interpretation

- AC-6 (least privilege): authorize the exact Assignment target before invoking a protected vacancy resolver, then independently authorize again at the authoritative mutation boundary.
- AU-3 (content of audit records): preserve the existing Assignment mutation's actor/purpose/evidence/audit-outbox contract rather than creating a parallel staffing store whose changes would not share the authoritative audit trail.

These references support the security-control design only. They do not imply NIST certification, employment-law compliance, or that a vacancy verification by itself authorizes an employment decision.
