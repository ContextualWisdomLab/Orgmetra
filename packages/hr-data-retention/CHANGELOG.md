# Changelog

## Unreleased

- Add `HrDataRetentionReviewPacket` as a value-minimized, human-review-required pre-disposition governance artifact.
- Bind authoritative tenant/resource, retention-policy digest, due date, legal-hold evidence, distinct requester/reviewer actors, evidence version, and exact UTC recorded time.
- Reject future values for the system-recorded timestamp so retention chronology cannot be forged.
- Fail closed under active holds and unexpired retention windows, and treat an elapsed due date only as a trigger for authoritative disposition review.
- Keep every packet explicitly `not_authorized_to_delete`; no automatic deletion, cross-service SQL, or foreign repository mutation is introduced.
- Revalidate all trust-bearing fields immediately before canonical audit serialization so low-level post-construction mutation cannot emit malformed legal-hold or noncanonical recorded-time evidence.
- Seal the creation-time canonical evidence digest in a process-local identity-keyed weak registry outside packet-writable state and reject later replacement even when the replacement policy digest, actor, date, or legal-hold evidence is independently well-formed; governed copy and pickle reconstruction receive independent seals.
- Make the trust-bearing packet runtime-final so a caller cannot subclass it and override derived non-authorizing state before canonical serialization.
- Add adversarial runtime-type, namespace, UUID, digest, chronology, separation-of-duties, replacement, serialization-time integrity, creation-seal, subclass-forgery, canonicalization, and exact 100% statement/branch coverage regressions.
