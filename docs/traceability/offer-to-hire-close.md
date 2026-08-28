# Offer-to-hire close traceability

## Status

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` already contains the governed `accept_confirmed_hire(...)` path. It authorizes one immutable `selection_decision` with purpose-bound policy before an injected mutation port may materialize Person, Employment, candidate-to-worker conversion, audit, and outbox facts.
- **Parent active PR:** #80 owns `CandidateOfferResponsePacket`, a value-minimized candidate-originated `offer_accepted` / `offer_declined` evidence packet that is explicitly `not_authorized_to_hire`.
- **This active stacked PR:** #108 first requires the authenticated principal to be purpose-bound to the exact hire selection decision, then connects an intact `offer_accepted` packet to the existing confirmed-hire path only after an authoritative host re-resolves candidate identity, candidate profile, exact offer approval/terms provenance, response identity, and the immutable selection decision.
- **Not shipped:** #108 is not protected-main truth and remains dependency-constrained on #80. Its checks/reviews must not be transferred from #80; after #80 integrates, this lane must retarget to fresh `develop` and obtain fresh exact-head People/Foundation/SAST/Security/Recovery evidence.

## Safety and authority contract

| Concern | Executable boundary |
|---|---|
| Authorization before sensitive resolution | `close_accepted_offer_to_hire(...)` purpose-authorizes the exact `selection_decision` and `candidate_worker_conversion` operation before invoking the candidate/offer authority resolver. Wrong-purpose, wrong-scope, or foreign-tenant callers therefore cannot use protected candidate/offer resolution as an oracle. |
| Candidate decline | With a valid hire authorization context, `offer_declined` stops before the authoritative resolver or hire mutation port. |
| Candidate response is not hire authority | The bridge accepts only canonical `CandidateOfferResponsePacket` evidence, then requires `CandidateOfferHireAuthority.verify_offer_acceptance(...)`; it never writes HR facts directly. |
| Tenant isolation | Candidate-response tenant must equal the `HireAcceptanceCommand` tenant, and the returned authority evidence must bind the same tenant. |
| Candidate linkage | The authority resolves the packet's opaque candidate-profile reference to the exact `candidate_profile_id` in the hire command. |
| Selection-decision linkage | The authority must bind the exact immutable `selection_decision_id` consumed by the protected confirmed-hire authorization path. |
| Offer provenance | Response SHA-256, offer-approval digest, offer-terms digest, and external candidate actor must exactly match the snapshotted candidate response. |
| Concurrent / post-construction response mutation | Candidate-response canonical evidence is verified before authority work and revalidated after it; a mutated packet fails closed before hire materialization. |
| Authority runtime integrity | `CandidateOfferHireVerification` is copied into an exact built-in/runtime-owned verification object and all UUID, digest, actor, and authority-reference fields are revalidated before use. |
| High-impact human/authorization boundary | The bridge delegates consequential mutation to existing `accept_confirmed_hire(...)`, which independently reauthorizes purpose, operation scope, authorized field set, authenticated principal, and exact selection-decision target immediately before persistence. |
| PII minimization | The bridge carries only correlation identifiers, evidence digests, candidate actor correlation, and the already-existing hire command. It does not duplicate offer compensation, candidate profile values, assessment scores, or free-form candidate text. |

## Executable evidence

`services/people-api/tests/test_offer_to_hire_close.py` defines regressions for decline-before-resolution, valid accepted-offer delegation, tenant/candidate/selection mismatches, evidence digest/actor mismatch, response mutation before and during authority work, runtime-type forgery, malformed authority evidence, and post-construction authority-evidence rewriting.

`services/people-api/tests/test_offer_to_hire_authorization_order.py` independently proves that a denied purpose-bound request cannot invoke the protected candidate/offer authority resolver or hire persistence boundary.

`.github/workflows/offer-to-hire-close-quality.yml` is the dedicated exact-head gate for this slice. The current stacked PR must remain Draft whenever this gate or any applicable integration gate is absent, queued, pending, cancelled, skipped, neutral, failed, stale, or otherwise non-terminal. A stack-local GREEN result would still not authorize merge before #80 integrates and the descendant is revalidated against fresh protected `develop`.

## Ownership

Orgmetra owns this bridge and the existing confirmed-hire application boundary. Keyverse remains the read-only identity owner through its published identity contract; #108 does not mutate Keyverse or query foreign application tables. Offer response remains candidate evidence, not an autonomous or model-derived employment decision.
