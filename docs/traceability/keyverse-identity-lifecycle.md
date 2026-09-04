# Keyverse identity lifecycle traceability

Status: Accepted on active PR; protected default branch `develop` does not contain this boundary until merged.

| Requirement | Orgmetra boundary | Evidence / test | External owner | Maturity |
|---|---|---|---|---|
| Queue identity deprovisioning without autonomous execution | `KeyverseIdentityDeprovisionReviewPacket` | fixed `requires_human_review`, `not_sent_to_keyverse`, `not_authorized_to_modify_identity` assertions | Keyverse SCIM remains read-only | implemented_on_active_pr |
| Re-resolve current employment and identity binding before any account mutation | canonical `scope_state` and `next_action` | canonical-document contract and exact Person/Employment/identity-binding references | Keyverse user resolution occurs only at the execution host | implemented_on_active_pr |
| Minimize identity/HR data in durable review evidence | digests + opaque correlation references | assertions exclude user ID, username, email and HR values; redacted repr | no Keyverse table reads | implemented_on_active_pr |
| Bind owner behavior to reviewed source | `keyverse_revision` + fixed reviewed operation | malformed/unreviewed revision rejection | `ContextualWisdomLab/keyverse@ce207dfd42975db61c82a5963e206fc1db14ac2b`, SCIM PATCH active=false | implemented_on_active_pr |
| Preserve immutable audit correlation before durable persistence | deterministic canonical JSON/SHA-256 + construction seal | post-construction mutation and missing-seal regressions | Orgmetra-owned | implemented_on_active_pr |
| Reject validation-forging runtime types | exact strings/integers/datetimes, final evidence type | hostile/wrong runtime, UUID, digest, version, time, future-time and subclass regressions | Orgmetra-owned | implemented_on_active_pr |

The packet is not an employment decision, a Keyverse mutation request that has been sent, or proof of human approval. A production host must still obtain explicit human confirmation and purpose-bound authorization after fresh authoritative Employment and identity-binding resolution. LLM output cannot satisfy those gates.
