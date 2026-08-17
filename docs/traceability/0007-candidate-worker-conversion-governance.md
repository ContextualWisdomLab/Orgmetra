# Candidate-to-worker conversion traceability

Status: Active PR #24; not protected-main truth.

| Requirement | Buyer-visible/control intent | Implementation | Executable evidence | Maturity |
|---|---|---|---|---|
| CWL-TA-001 | A candidate becomes a worker only through an explicit human-confirmed hire decision. | `validate_candidate_worker_conversion()` requires the same candidate, `decision_code = 'hire'`, actor, purpose, reason, confirmation, sealed evidence version, and at least one evidence member. | `tests/test_bitemporal_postgres.sh`: governed hire succeeds; legacy direct link and non-hire conversion fail closed. | Active PR #24 |
| CWL-HRIS-001 | Worker conversion identifies the resulting authoritative employment and person without conflating Candidate, Person, or Employment. | `candidate_worker_conversion_record` has separate candidate, person, employment, and decision foreign keys; the employment/person composite FK proves identity consistency. | Successful governed conversion fixture and relational constraints. | Active PR #24 |
| CWL-DATA-001 | Conversion history is reconstructable by business-effective and system-recorded time. | Half-open `effective_*` and `recorded_*` intervals, bitemporal GiST exclusion, and `protect_bitemporal_history()` correction guard. | Visibility-coordinate assertion, overlap denial, and in-place mutation denial. | Active PR #24 |
| CWL-SEC-001 | Candidate conversion remains tenant-isolated and does not create a new PII shadow record. | Tenant-qualified foreign keys, forced RLS, opaque references, and no copied names/assessment payloads. | Forced-RLS assertion plus existing tenant-scoped foundation constraints. | Active PR #24 |
| CWL-AUDIT-001 | Hiring provenance is linked to immutable versioned evidence rather than inferred later. | Conversion requires the exact sealed `selection_decision` and its non-empty `selection_decision_evidence` membership. | Human-confirmed hire fixture uses a sealed evidence set and versioned evidence member. | Active PR #24 |
| CWL-MIG-001 | Historical weak links are not silently upgraded with invented provenance. | New INSERTs to `candidate_worker_link` fail closed; historical rows remain append-only legacy records pending governed migration. | Direct legacy INSERT regression expects `candidate_worker_link is legacy-only`. | Active PR #24 |

## Dependency and release boundary

PR #24 is stacked on PR #23 exact head `c78aed423ae5c28b54caf6da389805ba5addce16`. PR #23 must integrate first. After any protected-base movement, #24 must be reconciled against the new protected `bootstrap` and all checks, reviews, coverage, and PostgreSQL contracts must be treated as fresh evidence. No predecessor check or review transfers.
