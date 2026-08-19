# Changelog

## Unreleased

- Add a PII-minimized, human-review-only performance-review evidence packet binding Employment/Job references while requiring downstream authoritative scope resolution before rating, together with performance cycle, criteria, goals, outcome evidence, optional development-plan provenance, and an accountable reviewer.
- Restrict `reason_code` to the reviewed closed vocabulary (`scheduled_cycle_review`) so arbitrary lower-snake-case text cannot carry PII or ungoverned decision context into canonical evidence.
- Bind a bounded positive `evidence_version` into canonical JSON and SHA-256 correlation evidence so high-impact review evidence versions are explicit and fail closed on invalid values.
