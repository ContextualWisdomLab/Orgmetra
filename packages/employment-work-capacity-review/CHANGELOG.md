# Changelog

## 0.1.0 - 2026-08-24

- Add governed Employment work-capacity review evidence.
- Bind exact four-decimal current/proposed capacity ratios to tenant, Employment, effective date, reviewed policy/terms evidence, reviewer identity evidence, human review, and system-recorded time.
- Reject signed negative zero so zero capacity has one canonical audit representation (`0.0000`).
- Generate `recorded_at` inside Orgmetra at issuance; callers cannot inject or backdate system-recorded evidence, and the generated time cannot precede `reviewed_at`.
- Require distinct requester/reviewer actors and keep the packet explicitly non-authoritative for Employment, Assignment, compensation, payroll, leave, and scheduling mutation.
- Add deterministic canonical JSON/SHA-256 evidence, redacted representations, post-issuance tamper detection, adversarial runtime-type tests, exact 100% owned statement/branch coverage, hash-bound wheel execution, and clean-checkout evidence.
