# Candidate Offer Response Traceability

## State legend

- **Protected-main truth**: already present on protected `develop` when this lane was cut.
- **Active PR**: implemented only on the candidate-offer-response branch until merged.
- **Dependency contract**: read-only interface owned elsewhere.
- **Out of scope**: intentionally not claimed by this slice.

## Requirement mapping

| Requirement | State | Evidence |
|---|---|---|
| Human offer approval is separate from candidate response | Protected-main truth | `packages/offer-approval`; ADR 0017 |
| Candidate-to-worker/confirmed-hire materialization is separately governed | Protected-main truth | `database/migrations/0009_candidate_worker_conversion_governance.sql`; People mutation boundary |
| Candidate response binds exact approved-offer and offer-terms digests | Active PR | `packages/candidate-offer-response/src/orgmetra_candidate_offer_response/response.py` |
| Acceptance and decline are both candidate-originated, closed-vocabulary evidence | Active PR | `response_code` allow-list plus adversarial tests |
| Employer-side shadow rejection is contractually barred, and the bar is enforced only by mandatory host-side re-resolution | Active PR | `candidate_actor_reference` and `identity_resolution_reference` are mandatory and no employer actor vocabulary exists, but the packet does not itself authenticate the candidate; fixed `scope_verification_state=requires_authoritative_resolution` makes consequential use without authoritative re-resolution a contract violation for downstream callers |
| Candidate actor correlation follows the published identity-owner boundary rather than an invented UUID version | Active PR + dependency contract | protected-main `packages/keyverse-adapter` accepts namespaced opaque actor references; `test_external_identity_reference_contract.py` proves a non-UUID Keyverse-compatible actor reference remains valid |
| Candidate response never directly authorizes hire or employment mutation | Active PR | fixed `employment_effect=not_authorized_to_hire`; governed `next_action` |
| Candidate identity is re-resolved before consequential downstream use | Active PR + dependency contract | fixed `scope_verification_state=requires_authoritative_resolution`; Keyverse remains read-only |
| Candidate PII, compensation values and free-form decline reasons are excluded | Active PR | fixed false sensitivity flags and canonical payload tests |
| Evidence preserves candidate response time and system-recorded time | Active PR | detached UTC `responded_at` / `recorded_at`; chronology regression |
| Caller-defined scalar/time subclasses cannot forge canonical evidence | Active PR | exact runtime type checks and hostile-subclass regressions |
| Post-construction rewriting invalidates evidence | Active PR | creation-time canonical digest seal plus mutation regressions |
| Canonical export emits the same snapshot that passed integrity validation | Active PR | `_assert_integrity()` returns the checked canonical bytes; `test_checked_snapshot_integrity.py` reproduces an interleaving valid-value rewrite and requires the previously checked snapshot to be emitted |
| Exact 100% owned statement/branch coverage | Active PR | `.github/workflows/candidate-offer-response-quality.yml` |
| Keyverse credentials or source state are never persisted here | Dependency contract | existing `packages/keyverse-adapter`; candidate-response packet stores opaque identity-resolution evidence only |
| Actual identity proofing/authentication assurance selection | Out of scope | authoritative identity owner / relying-party risk assessment |
| Offer eligibility, expiry, supersession and authoritative uniqueness | Out of scope for packet; required next step | owning talent-acquisition/offer workflow must re-resolve before action |
| Employment creation, assignment creation, compensation execution, offer delivery | Out of scope | existing owning HRIS boundaries |

## Architecture alignment

This slice does not introduce a new cross-service persistence path or a new architecture decision. It implements the existing Orgmetra principles in ADR 0001 (authoritative HRIS record), ADR 0006 (governed immutable audit/outbox evidence), ADR 0008 (purpose-bound PII authorization), and ADR 0017 (governed offer approval). It therefore adds no competing numbered ADR and does not edit the active canonical ADR index.

Keyverse remains read-only. The candidate actor is validated as a bounded namespaced opaque reference compatible with Orgmetra's protected-main Keyverse adapter; the response packet does not infer, rewrite, or constrain Keyverse's underlying OIDC `sub` to UUIDv4. `identity_resolution_reference` remains an Orgmetra-owned correlation reference with its explicit UUIDv4 contract and digest.

The candidate-response canonicalizer validates one payload snapshot against the process-local issuance seal and returns that same snapshot. It does not validate one read and then serialize the mutable object again. This preserves checked-versus-emitted audit integrity even if a same-process caller uses low-level mutation between those two phases; any later export from the changed packet still fails closed against the original issuance seal.

## Buyer outcome

A recruiter can no longer treat an approved offer as implicitly accepted, and an employer-side caller has no legitimate contract path to manufacture a decline through the candidate response: the packet carries opaque candidate identity evidence but never authenticates the candidate itself, so every consequential use must first re-resolve the authoritative identity boundary. The next actionable state is explicit: re-resolve candidate identity and exact offer scope, then use the owning employment boundary if and only if the response is verified as authoritative and eligible.