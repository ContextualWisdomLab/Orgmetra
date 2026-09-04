# Position lifecycle review — primary references

Reviewed 2026-08-24 (UTC/KST calendar date as applicable). These references support identifier, privacy-risk, and workforce-evidence design only; Orgmetra does not claim certification or reproduce licensed ISO metric definitions.

## APA 7 references

Davis, K., Peabody, B., & Leach, P. (2024). *Universally Unique IDentifiers (UUIDs)* (RFC 9562). RFC Editor. https://doi.org/10.17487/RFC9562

International Organization for Standardization. (2025). *Human resource management—Requirements and recommendations for human capital reporting and disclosure* (ISO 30414:2025, 2nd ed.). https://www.iso.org/standard/30414

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0* (NIST CSWP 10). https://doi.org/10.6028/NIST.CSWP.10

## Design use

- RFC 9562 is the primary identifier source for UUID layouts, including UUIDv4, UUIDv7, Nil, and Max. Orgmetra keeps authoritative HRIS operational UUID interoperability separate from packet-owned UUIDv4 correlation identifiers.
- ISO 30414:2025 is currently published as Edition 2 (2025-08) and includes workforce composition and mobility/succession among its human-capital reporting areas. It motivates historically defensible workforce/Position evidence, not a licensed metric implementation or conformity claim.
- NIST Privacy Framework 1.0 is a final, voluntary risk-management framework. It motivates value minimization and separating durable governance evidence from unnecessary Person/candidate/compensation payloads. NIST also lists Privacy Framework 1.1 as a newer project; this ADR does not present non-final work as the final baseline.
