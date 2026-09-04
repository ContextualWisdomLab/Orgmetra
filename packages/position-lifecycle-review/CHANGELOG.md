# Changelog

## 0.1.0 - Unreleased

- Add `PositionLifecycleChangeReviewPacket` for value-minimized human review of existing Position status changes.
- Keep all reviewed evidence non-authorizing until fresh authoritative bitemporal Position/Assignment resolution and immutable audit/outbox mutation.
- Reject no-op transitions, resurrection of abolished Positions, ungoverned status/reason/outcome vocabulary, noncanonical actor/digest/time evidence, hostile runtime scalar subclasses, post-issuance mutation, and conflicting live change-reference reuse.
- Add exact-head installed-wheel testing with exact 100% owned statement/branch coverage.
