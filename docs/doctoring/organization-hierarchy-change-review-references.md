# Organization hierarchy-change review references

Checked against the primary publishers on 2026-08-23. These references inform engineering choices; they do not imply certification or universal legal compliance.

## APA 7 references

National Institute of Standards and Technology. (2020). *NIST privacy framework: A tool for improving privacy through enterprise risk management, version 1.0*. U.S. Department of Commerce. https://doi.org/10.6028/NIST.CSWP.01162020

National Institute of Standards and Technology. (2025). *Security and privacy controls for information systems and organizations (NIST Special Publication 800-53 Rev. 5, Release 5.2.0)*. U.S. Department of Commerce. https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final

Davis, K., Peabody, B., & Leach, P. (2024). *Universally unique IDentifiers (UUIDs) (RFC 9562)*. RFC Editor. https://doi.org/10.17487/RFC9562

## Current-version notes

- NIST finalized SP 800-53 Release 5.2.0 on August 27, 2025. Orgmetra uses it as control-design context for accountable review, auditability, and separation of duties; this slice does not claim NIST certification.
- NIST's Privacy Framework site still presents Version 1.0 as the current final framework and labels Version 1.1 an Initial Public Draft / forthcoming update. The active PR therefore cites final PF 1.0 for normative architecture context and does not treat PF 1.1 draft text as final.
- RFC 9562, published May 2024, obsoletes RFC 4122 and defines UUID versions including UUIDv4 and UUIDv7 plus Nil and Max UUIDs. The packet uses that specification to distinguish packet-owned opaque UUIDv4 correlation from HRIS-owned operational UUID evolution.

## Design mapping

| Design choice | Primary evidence |
|---|---|
| Distinct requester/reviewer and later authoritative mutation | NIST SP 800-53 Rev. 5 Release 5.2.0, separation-of-duties/accountability control families |
| Data minimization and purpose-bound review evidence | NIST Privacy Framework 1.0 |
| Canonical UUID parsing, UUIDv4 packet correlations, UUIDv7-compatible HRIS references, sentinel rejection | RFC 9562 |
