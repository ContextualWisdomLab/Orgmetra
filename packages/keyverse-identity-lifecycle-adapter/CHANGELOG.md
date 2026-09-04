# Changelog

## Unreleased

- Add the governed `KeyverseIdentityDeprovisionReviewPacket` boundary.
- Bind tenant, Person, Employment, identity-binding provenance, requester, reviewed Keyverse revision, evidence version, and recorded time without copying identity or HR values.
- Reject system-recorded evidence timestamps that are later than the current UTC time.
- Keep deprovision evidence fail-closed at `requires_human_review`, authoritative employment/identity re-resolution required, not sent, and not authorized to modify identity.
- Pin the read-only Keyverse contract to `ce207dfd42975db61c82a5963e206fc1db14ac2b` and its SCIM active=false deactivation behavior.
- Add adversarial runtime-integrity tests, exact 100% owned statement/branch coverage, docstring checks, and a hash-bound installed-wheel quality workflow.
- Configure pytest to discover the package source directly without a manual `PYTHONPATH` override.
