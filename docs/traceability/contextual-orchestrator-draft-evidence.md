# Contextual Orchestrator draft-evidence traceability

## Truth state

- Protected-main truth at branch point `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`: the federated architecture names Contextual Orchestrator as a draft-evidence dependency, but the executable Orgmetra adapter is planned only.
- Active-PR truth: this branch adds an Orgmetra-owned, transport-neutral evidence envelope. It does not claim that Contextual Orchestrator, a particular provider, or a particular model is validated for employment decisions.
- Foreign-owner truth: `ContextualWisdomLab/contextual-orchestrator@e226e1197bdfc890c9d8e5b9b648c78857d7e465` is read-only here. Its published OpenAPI 0.1.0 contains authenticated `POST /v1/responses` requiring `model` and `input`.

## Requirement-to-evidence map

| Requirement | Implementation | Executable evidence |
|---|---|---|
| Model output is untrusted draft evidence | fixed `output_trust_state=untrusted_draft` | `test_builds_value_minimized_untrusted_human_review_evidence` |
| No autonomous high-impact employment decision | fixed `decision_authority_state=not_authorized_for_employment_decision` | `test_builds_value_minimized_untrusted_human_review_evidence` |
| Accountable human review is mandatory | distinct requesting/reviewing actor references and fixed `requires_human_review` state | `test_requires_requester_reviewer_separation` |
| Provenance is exact and value-minimized | input/response/provenance SHA-256 digests, dependency revision, API contract identifier/path, requested model alias | deterministic and invalid-evidence regressions in `test_envelope.py` |
| Foreign dedicated-writer boundary is preserved | no network client, foreign database access, or copied orchestrator implementation | package public surface exports only `DraftEvidenceEnvelope`; dependency contract is read-only evidence |
| Runtime evidence cannot be forged by caller subclasses | exact built-in trust primitives and final governed runtime type | hostile string/int/datetime and subclass regressions |
| Post-construction rewriting does not mint new audit evidence | process-local issuance seal checked before canonical serialization | `test_post_construction_rewrite_fails_closed`, `test_seal_rewrite_fails_closed`, `test_replacement_cannot_bypass_creation_evidence` |
| Owned code remains beginner-readable and exact-coverage gated | module/class/function docstrings and package pytest configuration | `test_docstrings.py` plus `--cov-branch --cov-fail-under=100` |

## Downstream handoff

`canonical_json()` and `evidence_digest()` are suitable correlation inputs for Orgmetra's immutable audit/outbox boundary. They are **not** authorization to persist HR business content, change employment state, rank a candidate, approve an offer, or trigger another service. Every such action must re-enter its own authoritative actor/purpose/scope/human-confirmation boundary.
