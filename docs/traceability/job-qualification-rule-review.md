# Job qualification-rule review traceability

## State boundary

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has authoritative Job Analysis Task/FJA/KSAO evidence but no dedicated governed qualification-rule review packet.
- **Active PR truth:** this branch proposes `JobQualificationRuleReviewPacket`; it is not protected-main truth until merged.
- **Foreign dependencies:** none are written or queried directly. This slice is Orgmetra-owned and standalone.

## Requirement-to-evidence matrix

| Requirement | Production boundary | Regression / gate |
|---|---|---|
| Tie proposed qualification rules to authoritative Job Analysis | Job + Job Analysis snapshot reference/digest | scope-ID and digest regressions |
| Preserve Task/KSAO/source provenance | independent Task, KSAO and source SHA-256 digests | malformed digest regressions |
| Avoid free-form sensitive rule storage | opaque qualification-rule artifact reference + digest and closed rule category | canonical privacy assertions |
| Keep job-rule design separate from candidate evaluation | fixed `not_authorized_for_candidate_or_employment_decision` | fixed-governance direct-construction tests |
| Preserve authoritative identifier ownership | tenant/Job/snapshot use non-sentinel operational UUIDs; packet-owned artifact/actors use UUIDv4 | namespace/sentinel/version regressions |
| Preserve business, review and system-recorded time separately | exact `effective_on`, exact UTC `reviewed_at`, owner-generated UTC `recorded_at` | type/timezone/future-review/caller-injection regressions |
| Require accountable human review | distinct requester/reviewer UUIDv4 correlations and mandatory review state | actor-overlap and governance regressions |
| Version high-impact evidence | bounded exact integer `evidence_version` | bool/non-int/range and digest-change regressions |
| Detect in-process post-issuance mutation | process-local weak issuance digest outside packet slots; export revalidates one snapshot | valid-field and hostile-runtime mutation regressions |
| Preserve exact package/artifact evidence | dedicated exact-head workflow builds and SHA-256-binds isolated wheel | Job Qualification Rule Review Quality |
| Preserve exact owned test sufficiency | package pytest config requires statement and branch coverage 100% | `--cov-fail-under=100`, branch coverage enabled |

## Authoritative next action

Before a reviewed rule may alter Job/Job Analysis truth or influence applicant screening or selection, the Orgmetra host must re-resolve the exact tenant, Job, Job Analysis snapshot, qualification-rule artifact, Task/KSAO/source evidence, reviewer identity and authority, and current business-time context. Any authoritative change must preserve human confirmation and immutable audit/outbox evidence atomically.

The packet does not decide whether an applicant satisfies a rule, whether a rule is lawful or validated, or whether any employment action should occur. LLM output remains untrusted draft evidence only.
