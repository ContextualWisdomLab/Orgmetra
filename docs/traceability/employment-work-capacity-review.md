# Employment work-capacity review traceability

## State boundary

- **Protected main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has distinct Employment and Assignment facts but no dedicated governed review evidence for changing one Employment's overall work-capacity ratio.
- **Active PR truth:** PR #103 proposes `EmploymentWorkCapacityReviewPacket`; it is not protected-main truth until merged.
- **Foreign dependencies:** none are written or queried directly. This package is Orgmetra-owned and standalone.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression / gate |
|---|---|---|
| Keep Employment capacity distinct from Assignment allocation | `EmploymentWorkCapacityReviewPacket.current_capacity_ratio` / `proposed_capacity_ratio` | canonical evidence tests require both ratios and no Assignment mutation authority |
| Preserve authoritative HRIS identifier ownership | canonical non-sentinel tenant UUID and `employment_record:<uuid>` reference without leaf UUID-version restriction | malformed/Nil/Max/wrong-namespace regressions |
| Bind reviewed capacity values deterministically | exact built-in `Decimal`, finite `[0.0000, 1.0000]`, exactly four decimal places, signed negative zero rejected | type, range, NaN, signed-zero, scale and no-op regressions |
| Preserve business, review, and system-recorded time separately | exact `effective_on`; exact UTC `reviewed_at`; `recorded_at` generated inside Orgmetra at issuance and required to be no earlier than review | date/timezone/future-review and builder-ownership regressions |
| Require accountable human review | distinct requester/reviewer UUIDv4 correlations plus reviewer identity digest and fixed human-review state | actor-overlap, fixed-state and identity-evidence regressions |
| Bind exact reviewed evidence | lowercase SHA-256 digests for employment terms, capacity policy/definition and reviewer identity resolution | malformed/non-text digest regressions |
| Minimize durable evidence | controlled reason vocabulary; no name/email/phone/salary/rating/free-form text/prompt/model output | canonical-evidence privacy assertions and redacted `repr()` |
| Prevent the packet from becoming mutation authority | fixed `not_authorized_to_change_employment_or_compensation` and governed next action | fixed-governance rewrite regressions |
| Detect post-issuance in-process mutation | process-local weak issuance digest outside packet fields; export verifies one payload snapshot | `object.__setattr__` mutation regression |
| Preserve exact package/artifact evidence | dedicated exact-head workflow builds and SHA-256-binds the wheel, runs installed artifact, requires clean checkout | Employment Work Capacity Review Quality |
| Preserve exact owned test sufficiency | package pytest configuration requires statement and branch coverage 100% | `--cov-fail-under=100`, branch coverage enabled |

## Authoritative next action

Before applying a reviewed work-capacity change, the Orgmetra host must re-resolve the same tenant and Employment, verify the current capacity truth at the business-effective coordinate, re-establish reviewer identity and authority, verify the exact employment-terms and capacity-policy evidence, calculate Assignment-allocation and compensation/payroll implications, and atomically persist the approved bitemporal change with immutable audit/outbox evidence.

The packet does not classify legal full-time/part-time status, determine worker suitability, infer availability for specific work, or authorize scheduling, leave, compensation, payroll, Assignment, or Employment mutation.
