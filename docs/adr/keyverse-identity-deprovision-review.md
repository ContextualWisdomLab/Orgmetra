# ADR: Govern identity deprovisioning as a non-executing review packet

Status: Accepted on active PR; protected default branch `develop` does not contain this boundary until merged.

## Context

Orgmetra owns employment truth and domain authorization; Keyverse owns identity provisioning and account state. The foundation architecture identifies Keyverse OIDC/SCIM as the first external identity adapter, but directly translating an HR lifecycle observation into a Keyverse deactivation would collapse the service boundary and make stale or unreviewed HR evidence capable of removing access.

Keyverse `main@ce207dfd42975db61c82a5963e206fc1db14ac2b` exposes the SCIM v2 public path `PATCH /scim/v2/Users/{user_id}` and deactivates when `active=false`. That repository is a dedicated-writer dependency and remains read-only here.

## Decision

Orgmetra emits only a `KeyverseIdentityDeprovisionReviewPacket`. The packet:

- binds tenant, Person, Employment, identity-binding provenance, requester, reviewed owner revision, evidence version, and system-recorded time;
- omits the Keyverse user ID and identity/HR values from durable canonical evidence;
- fixes state to `requires_human_review`, authoritative Employment/identity re-resolution required, not sent, and not authorized to modify identity;
- provides a safe next action rather than a network client;
- fails closed on ambiguous runtime types, unreviewed owner revisions, or post-construction evidence mutation.

The execution host, if later implemented, must re-resolve current Employment and identity binding, verify explicit human confirmation and purpose-bound authority, then call only a published Keyverse contract. An LLM or this packet alone cannot authorize the operation.

## Consequences

This preserves standalone Orgmetra operation and a modular MSA extraction boundary. It also makes deprovision intent auditable before side effects while avoiding foreign table coupling. The tradeoff is deliberate: this slice does not automate identity mutation yet. Execution, delivery idempotency, owner response evidence, rollback/reconciliation, and lifecycle provisioning remain separate bounded work after this review boundary is integrated.
