# Orgmetra Candidate Offer Response

This package records a **candidate-originated response to one exact reviewed offer** without turning that response into employment authority.

## What it does

`build_candidate_offer_response(...)` produces immutable, value-minimized evidence that binds:

- one Orgmetra tenant;
- one candidate profile;
- one exact human-reviewed offer approval and SHA-256 digest;
- one exact offer-terms reference and SHA-256 digest;
- one authenticated candidate actor plus identity-resolution evidence;
- the closed response code `offer_accepted` or `offer_declined`;
- the candidate response instant and the later/equal system-recorded instant; and
- one bounded evidence version.

The packet normalizes caller timestamps to built-in UTC values at construction, rejects caller-defined subclasses at trust-bearing scalar boundaries, redacts routine `repr`, and seals its canonical construction digest so later field rewriting is rejected before serialization.

Orgmetra-owned packet/evidence references keep their reviewed canonical UUIDv4 suffix contract. `candidate_actor_reference` is different: it is an opaque actor correlation supplied by the approved identity boundary, so this package validates the exact `candidate:` namespace and a bounded opaque token without inventing a UUID version requirement. The authoritative identity boundary must still re-resolve the actor before consequential use.

## What it deliberately does not do

An accepted response is **not** authorization to hire, create employment, create an assignment, convert a candidate to a worker, send another offer, execute compensation, or mutate Keyverse. The packet therefore always carries `employment_effect=not_authorized_to_hire` and `scope_verification_state=requires_authoritative_resolution`.

The packet also contains no candidate PII, compensation values, free-form decline reason, credentials, tokens, or LLM output. A decline is candidate-originated evidence; it is not an employer-side rejection shortcut.

## Required next action

Before any consequential action, the authoritative workflow must re-resolve the candidate actor through the approved identity boundary, re-resolve the exact offer approval and offer-terms digests, verify that the offer was eligible for response at `responded_at`, and establish that this is the authoritative candidate response. Confirmed-hire materialization remains the responsibility of the existing People/candidate-to-worker boundary.

Keyverse is a read-only dependency from this package's perspective. Orgmetra stores only the opaque identity-resolution evidence needed to correlate the candidate action; it stores no Keyverse credentials.

## Example

```python
from datetime import datetime, timezone
from orgmetra_candidate_offer_response import build_candidate_offer_response

packet = build_candidate_offer_response(
    tenant_record_id="018f6e2a-4f7c-7a1b-9c20-1f3a7d8e5b60",
    offer_response_reference="candidate_offer_response:6ba7b810-9dad-4b11-80b4-00c04fd430c8",
    candidate_profile_reference="candidate_profile:6ba7b811-9dad-4b11-80b4-00c04fd430c8",
    offer_approval_reference="offer_approval:6ba7b812-9dad-4b11-80b4-00c04fd430c8",
    offer_approval_digest="a" * 64,
    offer_terms_reference="offer_terms:6ba7b813-9dad-4b11-80b4-00c04fd430c8",
    offer_terms_digest="b" * 64,
    candidate_actor_reference="candidate:AItOawmwtWwcT0k51BayewNvutrJUqsvl6qs7A4",
    identity_resolution_reference="identity_resolution:6ba7b815-9dad-4b11-80b4-00c04fd430c8",
    identity_resolution_digest="c" * 64,
    response_code="offer_accepted",
    responded_at=datetime(2026, 8, 22, 9, 30, tzinfo=timezone.utc),
    recorded_at=datetime(2026, 8, 22, 9, 30, 1, tzinfo=timezone.utc),
)
```

Persist or publish `packet.canonical_json()` only through the owning Orgmetra audit/outbox boundary after authoritative scope resolution. Never treat `packet.sha256_digest()` alone as identity, approval, or hire authority.
