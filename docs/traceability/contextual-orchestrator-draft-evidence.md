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
| Accountable human review is mandatory | distinct opaque `actor:` UUIDv4 requester/reviewer correlations and fixed `requires_human_review` state | `test_requires_requester_reviewer_separation`, `test_rejects_human_readable_actor_correlation` |
| Durable actor evidence excludes human-readable handles | `_validate_actor_reference` delegates to canonical UUIDv4 reference validation | `test_rejects_human_readable_actor_correlation` plus invalid-governance regressions |
| System-recorded time is not caller-controlled | `recorded_at` is `init=False` and generated at issuance from the built-in UTC clock | `test_system_recorded_time_is_not_a_caller_constructor_argument`, `test_builds_value_minimized_untrusted_human_review_evidence` |
| Every replacement is visibly new evidence | `draft_evidence_reference` and `recorded_at` are init-disabled and regenerated for every construction/replacement | `test_replacement_is_a_new_system_recorded_evidence_issuance`, `test_replacement_is_a_distinct_system_recorded_issuance` |
| Provenance is exact and value-minimized | input/response/provenance SHA-256 digests, dependency revision, API contract identifier/path, requested model alias | deterministic and invalid-evidence regressions in `test_envelope.py` |
| Foreign dedicated-writer boundary is preserved | no network client, foreign database access, or copied orchestrator implementation | package public surface exports only `DraftEvidenceEnvelope`; dependency contract is read-only evidence |
| Runtime evidence cannot be forged by caller subclasses | exact built-in trust primitives and final governed runtime type | hostile string/int and subclass regressions |
| Accidental in-process object rewriting is detected before export | process-local HMAC snapshot checked before canonical serialization; constructor exposes neither seal nor issuance marker | post-construction field/time/reference/seal regressions and `test_internal_integrity_state_is_not_constructor_visible` |
| Checked evidence cannot diverge from emitted evidence | `_assert_integrity()` snapshots live fields once, verifies the canonical bytes for that exact snapshot against the creation seal, and returns the same verified snapshot/bytes to both export paths | `test_canonical_json_emits_the_exact_snapshot_that_passed_integrity`, `test_canonical_document_returns_the_verified_snapshot_without_rereading` |
| Process-local detection is not claimed as durable tamper prevention | README/ADR explicitly assign durable uniqueness/authorization/immutability to authoritative audit/outbox persistence | documentation contract plus replacement/new-issuance regressions |
| Owned code remains beginner-readable and exact-coverage gated | recursive module/class/function docstring inventory and package pytest configuration | `test_docstrings.py` plus `--cov-branch --cov-fail-under=100` |

## Downstream handoff

`canonical_json()` and `evidence_digest()` are suitable correlation inputs for Orgmetra's immutable audit/outbox boundary. Both canonical export methods now return only the single snapshot whose canonical bytes passed the creation-time integrity check; they do not reread live fields after validation. They are **not** authorization to persist HR business content, change employment state, rank a candidate, approve an offer, or trigger another service. Every such action must re-enter its own authoritative actor/purpose/scope/human-confirmation boundary. Durable audit/outbox persistence owns cross-process uniqueness and tamper evidence; the Python object does not claim to replace that authority.