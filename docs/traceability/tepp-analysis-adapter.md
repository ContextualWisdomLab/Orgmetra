# TEPP analysis adapter traceability

| Requirement | Orgmetra evidence | Verification | Maturity |
|---|---|---|---|
| No foreign table access or duplicated TEPP kernels | `orgmetra_tepp_adapter.analysis` contains only request/governance binding logic | package source review; no TEPP runtime dependency | implemented_on_active_pr |
| Exact TEPP analysis-run v1 request shape | `TeppAnalysisRequestPacket.tepp_request()` | exact seven-field regression against reviewed TEPP DTO | implemented_on_active_pr |
| Temporal cutoff provenance | timezone-aware `knowledge_cutoff` and `generated_at` → detached exact UTC instants and canonical RFC 3339 UTC | mutable-timezone stability, provider-failure, malformed-offset, arithmetic-overflow, naive/null-offset, and datetime-subclass rejection tests | implemented_on_active_pr |
| Tenant/study/actor governance | authoritative canonical non-sentinel operational tenant UUID plus namespaced UUIDv4 Orgmetra references | protected-core UUIDv7 interoperability plus nil/max/noncanonical tenant rejection; wrong-namespace/reference-version regressions | implemented_on_active_pr |
| Immutable analytical snapshot evidence | opaque TEPP snapshot ID plus independent SHA-256 `snapshot_digest` | digest format and governance-evidence regressions | implemented_on_active_pr |
| Durable idempotency handoff | `idempotency_key` + deterministic `request_digest()` + `governance_scope_digest()` | exact-retry and same-key request/scope conflict regressions | implemented_on_active_pr |
| Privacy minimization without anonymity claims | `contains_personal_data=true`; direct identity/source text/credentials false; redacted repr | direct-construction/replace/privacy regressions | implemented_on_active_pr |
| High-impact human review | fixed `human_scientific_review_only`, `untrusted_draft_evidence`, governed `next_action` | authority-expansion regressions | implemented_on_active_pr |
| Foreign runtime maturity is not overstated | `transport_state=requires_published_tepp_service_contract` | fixed-state regression and package/ADR documentation | implemented_on_active_pr |
| Exact owned production coverage | package pytest-cov gate | 100% statement + branch coverage | implemented_on_active_pr |

## Foreign evidence snapshot

Reviewed TEPP protected `main`: `7c29e7c971d7940e1fb3def1ed3aae2d1bc8ad4a`. The reviewed `crates/tepp_api/src/analysis_run.rs` defines contract version `1` and the seven request fields above; `docs/API_CONTRACT.md` states that protected main exposes library/domain contracts rather than a production HTTP service. Orgmetra must re-resolve this evidence before enabling transport.
