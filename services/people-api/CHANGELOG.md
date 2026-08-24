# People API changelog

## Unreleased

### Added

- Add `close_accepted_offer_to_hire(...)` as a governed bridge from an intact candidate `offer_accepted` evidence packet to the existing authoritative confirmed-hire path.
- Add `CandidateOfferHireAuthority` and redacted `CandidateOfferHireVerification` contracts so candidate identity, candidate profile, exact offer provenance, and immutable selection decision are re-resolved before any hire materialization.
- Add fail-closed regressions for decline handling, tenant/candidate/selection mismatch, evidence mismatch, response tampering, authority-evidence runtime forgery, and post-construction rewriting.

### Security / governance

- Candidate offer response remains necessary but non-authorizing evidence; it cannot directly create Person, Employment, or candidate-to-worker facts.
- Consequential authorization remains in the existing purpose-bound `accept_confirmed_hire(...)` boundary.
- This change is stacked on candidate-offer-response PR #80 and is not protected-main truth until its parent integrates and this descendant is freshly revalidated against protected `develop`.
