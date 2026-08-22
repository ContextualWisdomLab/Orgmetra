# Changelog

## 0.1.0 — Unreleased

- Add value-minimized `HrAccessReviewPacket` evidence for retaining, reducing, or removing existing HR access.
- Require an independent reviewer and exact tenant/actor/scope/policy/entitlement provenance.
- Bind reviewer identity-resolution evidence, the fixed `hr_access_recertification` purpose, and distinct human-review/system-recorded UTC times; reject system-recorded evidence that predates the review.
- Keep every packet non-enforcing with authoritative re-resolution required before any access mutation.
- Reject hostile runtime subclasses and post-construction evidence rewrite.
- Add exact-head CI requiring 100% owned statement and branch coverage.
