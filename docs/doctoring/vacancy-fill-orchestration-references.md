# Vacancy fill orchestration references

Reviewed 2026-08-25 (Release 5.2.0 planning-note evidence).

## Primary standards

National Institute of Standards and Technology. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). U.S. Department of Commerce. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2025). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53 Revision 5, current release 5.2.0). Computer Security Resource Center. https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final

## Applied interpretation

- AC-6 (least privilege): authorize the exact Assignment target before invoking a protected vacancy resolver, then independently authorize again at the authoritative mutation boundary.
- AU-3 (content of audit records): preserve the existing Assignment mutation's actor/purpose/evidence/audit-outbox contract rather than creating a parallel staffing store whose changes would not share the authoritative audit trail. The AU-3 discussion was among the related-control updates in Release 5.2.0, issued August 27, 2025; this design cites the control's content-of-audit-records requirement as of that release and does not claim any later errata state.

These references support the security-control design only. They do not imply NIST certification, employment-law compliance, or that a vacancy verification by itself authorizes an employment decision.
