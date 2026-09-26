# External delivery receipt — primary references

These references support only the narrow cryptographic/time representation decisions in
PR #151. They do not imply certification, provider authenticity, delivery guarantees, or
employment-law compliance.

## APA 7 references

National Institute of Standards and Technology. (2015). *Secure Hash Standard (SHS)*
(FIPS PUB 180-4). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.180-4

National Institute of Standards and Technology. (2023, March 7). *Decision to revise FIPS
180-4, Secure Hash Standard (SHS).* https://csrc.nist.gov/News/2023/decision-to-revise-fips-180-4

Sharma, U., & Bormann, C. (2024). *Date and time on the Internet: Timestamps with
additional information* (RFC 9557). RFC Editor. https://doi.org/10.17487/RFC9557

## Decision notes

- SHA-256 is used for content correlation, not signing. NIST's current CAVP secure-hashing
  material continues to list SHA-256 in the SHA-2 family under FIPS 180-4; NIST has also
  announced that FIPS 180-4 will be revised.
- RFC 9557 updates RFC 3339's interpretation of the `Z` local-offset marker. Orgmetra uses
  `Z` only to produce one deterministic UTC/zero-offset text representation for evidence
  hashing; it does not encode a source time zone.
