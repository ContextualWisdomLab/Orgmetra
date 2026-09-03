# Workforce composition change traceability

| Requirement | Orgmetra evidence | Verification | Maturity |
|---|---|---|---|
| Compare business-time workforce states without knowledge-time drift | `WorkforceCompositionChangeSnapshot` requires identical endpoint `known_at` values, rechecks them immediately before canonical export, and the builder freezes one cutoff before both endpoints | different-cutoff, sequenced-timezone-provider, and post-construction cutoff-mutation regressions | implemented_on_active_pr |
| Preserve tenant isolation | endpoint tenants must match at construction and immediately before canonical export; builder supplies one tenant to both existing snapshots | cross-tenant direct-construction rejection plus post-construction tenant-mutation export rejection | implemented_on_active_pr |
| Require a real forward comparison | opening `effective_on` must be earlier than closing `effective_on` at construction and immediately before canonical export | equal-date rejection, post-construction date-order mutation rejection, and buyer-readable next action | implemented_on_active_pr |
| Require exact validated endpoint evidence | both endpoints must remain exact `WorkforceCompositionSnapshot` runtime values; subclasses and low-level endpoint replacement cannot bypass the canonical endpoint contract | forged-subclass construction regressions plus post-construction endpoint-type mutation rejection | implemented_on_active_pr |
| Reuse authoritative HRIS integrity | both endpoints call `build_workforce_composition_snapshot(...)`; endpoint `canonical_json()` rechecks its own canonical workforce invariants during comparison export | existing complete HRIS-kernel workforce/integrity suite plus change and mutation regressions | implemented_on_active_pr |
| Keep workforce intelligence descriptive | only net aggregate deltas are exposed; no hire/separation/turnover/cause/recommendation label exists | public API and canonical-schema review | implemented_on_active_pr |
| Preserve exact FTE arithmetic | staffed FTE change uses exact Decimal coefficient arithmetic over canonical four-decimal endpoints | realistic `1.0000` delta, caller Decimal-context parity, and canonical endpoint-FTE regressions | implemented_on_active_pr |
| Avoid row-level shadow HR data | canonical comparison embeds aggregate endpoint JSON/digests only | canonical output excludes `person_record_id` and all endpoint row identities by construction | implemented_on_active_pr |
| Deterministic audit correlation | canonical JSON + SHA-256 content digest are emitted only after cross-endpoint and endpoint-level invariant revalidation | reordered-source equality plus post-construction tenant/date/cutoff/type mutation fail-closed regressions | implemented_on_active_pr |
| Current standards traceability | ADR-0024 + doctoring record for ISO 30414:2025 and ISO 30400:2022 public metadata | official ISO catalogue rechecked August 20, 2026 | implemented_on_active_pr |
| Exact owned production coverage | `Workforce Intelligence Quality` runs complete HRIS kernel | package pytest-cov requires 100% statement and branch coverage | implemented_on_active_pr |

## Buyer interpretation

A positive or negative endpoint delta says only that aggregate composition differs between two effective dates when reconstructed with the same system-knowledge cutoff. It is not evidence that a particular person was hired, separated, transferred, promoted, retained, or caused the change. Event-specific mobility and turnover claims require separately governed employment-transition evidence and an explicit denominator/period policy.
