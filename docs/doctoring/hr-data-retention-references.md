# HR Data Retention Review — Primary References

Status: **active PR research evidence**, not protected-main product truth and not a certification claim.

The implementation uses these sources as governance design inputs. It intentionally does **not** encode one universal legal retention period. Applicable law, jurisdiction, employer type, record category, litigation/charge status, contractual obligations, and organizational policy must be authoritatively resolved by the host before disposition.

## APA 7 references

Joint Task Force. (2020). *Security and privacy controls for information systems and organizations* (NIST Special Publication 800-53, Revision 5). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-53r5

National Institute of Standards and Technology. (2020). *NIST privacy framework: A tool for improving privacy through enterprise risk management, version 1.0*. https://doi.org/10.6028/NIST.CSWP.01162020

U.S. Equal Employment Opportunity Commission. (n.d.). *Recordkeeping requirements*. Retrieved August 22, 2026, from https://www.eeoc.gov/employers/recordkeeping-requirements

U.S. Equal Employment Opportunity Commission. (n.d.). *Summary of selected recordkeeping obligations in 29 CFR Part 1602*. Retrieved August 22, 2026, from https://www.eeoc.gov/employers/summary-selected-recordkeeping-obligations-29-cfr-part-1602

## Design implications

- NIST Privacy Framework 1.0 treats retention and disposal as data-life-cycle actions, supporting an explicit governed transition between retention review and any later disposition execution.
- NIST SP 800-53 Rev. 5 integrates privacy controls with security and accountability controls, supporting immutable policy/actor/evidence binding rather than an unaudited date-driven delete.
- Current EEOC guidance demonstrates why a single hard-coded period is unsafe: covered personnel/employment records can have different minimum periods, and charge-related records must remain available through final disposition.
- Therefore the Orgmetra packet binds the exact reviewed policy reference/digest and legal-hold evidence, but remains `not_authorized_to_delete` even after the reviewed due date has passed.
