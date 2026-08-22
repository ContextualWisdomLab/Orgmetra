# HR Data Disposition Request — Primary References

## Scope

These sources inform the design of Orgmetra's application-layer disposition-request boundary. They do not establish a universal legal retention period, do not replace jurisdiction-specific legal review, and do not establish that application deletion equals storage-media sanitization.

## APA 7 references

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0*. U.S. Department of Commerce. https://doi.org/10.6028/NIST.CSWP.01162020

Chandramouli, R., & Hibbard, E. (2025). *Guidelines for media sanitization* (NIST Special Publication 800-88 Rev. 2). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-88r2

## Design implications recorded for this slice

1. NIST Privacy Framework 1.0 treats review, alteration, deletion, destruction according to policy, processing permissions, and audit/log records as distinct governable data-processing capabilities. Orgmetra therefore does not infer destructive authority merely because a retention due date has elapsed.
2. A disposition request carries only the minimum opaque governance evidence needed to support the next accountable review. It does not carry HR payload values.
3. The request requires explicit human review and remains `not_authorized_to_execute`; a future executor must independently re-resolve current scope and authority rather than trusting stale packet state.
4. NIST SP 800-88 Rev. 2, finalized September 26, 2025, treats media sanitization as an enterprise storage/media assurance program whose goal is to render access to target data infeasible for a relevant effort level. Application-layer deletion or pseudonymization cannot itself prove that outcome.
5. Orgmetra therefore records `media_sanitization_state=not_claimed`. Any later sanitization validation belongs to the storage/infrastructure owning boundary and must be linked by published evidence contracts rather than inferred from an application request.
