# Release readiness review traceability

## Truth status

- Protected-main source at branch creation: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- This document describes **active-PR truth only** until PR #118 is integrated.
- Release artifact/provenance generation and deployment reference work in other active Orgmetra PRs are dependencies by evidence digest only; their checks or reviews do not transfer into this PR.

## Requirement mapping

| Requirement | Owner boundary | Evidence | Verification |
|---|---|---|---|
| Exact candidate identity | release-readiness review | non-null 40-hex `candidate_revision_sha` | exact runtime type, canonical lower-hex, and Git null-OID rejection regressions |
| Complete reviewed release evidence | release-readiness review | source, SBOM, provenance, tests, coverage, security, SAST, recovery, operability, accessibility, migration/rollback, package-reproducibility SHA-256 digests | each digest is independently required and validated |
| Human accountability | release-readiness review | distinct pseudonymous requester/reviewer plus `reviewed_at` | UUIDv4-format actor correlation, separation, exact UTC time |
| System time | release-readiness review | `recorded_at` | Orgmetra-owned UTC issuance; cannot precede human review |
| No implicit release authority | release-readiness review | fixed governance state | `requires_human_review`, `requires_protected_head_verification`, `not_authorized_to_release` |
| Evidence integrity | release-readiness review | creation-time canonical digest outside packet fields | valid post-issuance mutation fails before export |
| Exact owned coverage | dedicated workflow | installed exact-checkout package | 100% statement and branch coverage |
| Reproducible package evidence | dedicated workflow | reviewed build-backend hash plus locally computed wheel hash | `pip --require-hashes`, isolated target import, clean checkout |

## Explicit non-goals

The packet does not prove that a revision is the current default-branch head, does not itself execute GitHub rules, does not grant release authority, and does not tag, sign, publish, deploy, or mutate another CWL repository. The authoritative release operation must perform fresh live verification immediately before release.
