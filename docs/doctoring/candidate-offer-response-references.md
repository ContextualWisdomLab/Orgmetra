# Candidate Offer Response — Standards and Research Notes

## Evidence status

These references inform the candidate-response trust boundary. They do **not** claim that Orgmetra, an identity provider, or a customer deployment is NIST-certified, NIST-conformant, SOC 2 certified, or compliant with any employment law merely because the design cites them.

## Design implications

1. **Identity must be evidence, not a caller assertion.** NIST SP 800-63 Revision 4 is the current final Digital Identity Guidelines suite (July 2025) and treats identity proofing, authentication, federation, security, privacy, and customer experience as risk-managed digital identity functions. Orgmetra therefore records only an opaque candidate actor plus identity-resolution evidence and requires authoritative re-resolution before relying on the response.
2. **Minimize candidate data at the response boundary.** NIST Privacy Framework 1.0 is a risk- and outcome-based enterprise privacy framework. The candidate-response packet excludes candidate PII, compensation values and free-form decline reasons because those values are unnecessary to prove the response event itself.
3. **Do not invent a UUID version for an external identity.** OpenID Connect Core defines `sub` as a case-sensitive, locally unique, never-reassigned subject string of at most 255 ASCII characters and relies on the `(iss, sub)` pair for stable cross-issuer identity. Keyverse protected-main product requirements likewise make exact `(identity_provider, subject)` the strongest matching evidence and require RPs to validate issuer and subject; they do not publish a UUIDv4-only subject contract. Orgmetra's protected Keyverse adapter therefore accepts a namespaced opaque `actor_reference`. Candidate-offer-response preserves that owner boundary: its `candidate_actor_reference` is bounded namespaced opaque text and is re-resolved authoritatively before consequential use.
4. **Packet-owned references keep their explicit identifier contract.** RFC 9562 is the current standards-track UUID specification and obsoletes RFC 4122. Orgmetra-owned packet/evidence correlation references in this slice use canonical non-sentinel UUIDv4 suffixes; the Orgmetra tenant identifier remains an authoritative operational UUID and may use the repository's UUIDv7 convention. The UUIDv4 rule is not projected onto the externally owned candidate actor.
5. **Acceptance is not employment authority.** Digital identity evidence establishes who acted; it does not establish that an approved offer is still eligible, unique, unsuperseded, or sufficient to create employment. Those facts stay at their authoritative Orgmetra boundaries and must be re-resolved before consequential mutation.

## APA 7 references

Davis, K., Peabody, B., & Leach, P. (2024). *Universally unique IDentifiers (UUIDs)* (RFC 9562). Internet Engineering Task Force. https://doi.org/10.17487/RFC9562

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, version 1.0* (NIST CSWP 10). U.S. Department of Commerce. https://doi.org/10.6028/NIST.CSWP.10

Temoshok, D., Proud-Madruga, D., Choong, Y.-Y., Galluzzo, R., Gupta, S., LaSalle, C., Lefkovitz, N., & Regenscheid, A. (2025). *Digital identity guidelines* (NIST Special Publication 800-63-4). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-63-4

OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set 2*. https://openid.net/specs/openid-connect-core-1_0.html

## Primary-source verification

- CSRC records SP 800-63-4 with document date **July 2025** (`Date Published: July 2025`, document-history final entry `07/31/25`); NIST's public announcement of the final suite followed on August 1, 2025. The two dates refer to different events and are both retained here.
- Official CSRC author order for SP 800-63-4: David Temoshok, Diana Proud-Madruga, Yee-Yin Choong, Ryan Galluzzo, Sarbari Gupta, Connie LaSalle, Naomi Lefkovitz, Andrew Regenscheid. The APA entry preserves this exact order.
- NIST published final SP 800-63 Revision 4 in July 2025; it supersedes SP 800-63-3.
- NIST Privacy Framework 1.0 was published January 16, 2020 and remains the final 1.0 publication while newer Privacy Framework work is developed separately.
- RFC 9562 was published May 2024 as an IETF Standards Track RFC and obsoletes RFC 4122.
- OpenID Connect Core specifies `sub` as a case-sensitive string, not a UUID, and makes `(iss, sub)` the stable identity pair available to the relying party.
- Keyverse protected `main` documents exact `(identity_provider, subject)` matching and issuer/subject validation without a UUIDv4-only subject guarantee; Orgmetra does not mutate Keyverse to change that contract.
