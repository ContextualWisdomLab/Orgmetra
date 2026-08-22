# Changelog

## Unreleased

- Add `HrDataRetentionReviewPacket` as a value-minimized, human-review-required pre-disposition governance artifact.
- Bind authoritative tenant/resource, retention-policy digest, due date, legal-hold evidence, distinct requester/reviewer actors, evidence version, and exact UTC recorded time.
- Fail closed under active holds and unexpired retention windows, and treat an elapsed due date only as a trigger for authoritative disposition review.
- Keep every packet explicitly `not_authorized_to_delete`; no automatic deletion, cross-service SQL, or foreign repository mutation is introduced.
- Add adversarial runtime-type, namespace, UUID, digest, chronology, separation-of-duties, replacement, canonicalization, and exact 100% statement/branch coverage regressions.
