# Orgmetra Keyverse Identity Lifecycle Adapter

This package creates a **non-executing deprovision review packet** for an Orgmetra employment-driven identity lifecycle action. It exists so HR operations can queue a reviewable next action without turning an HR record, an LLM suggestion, or a caller-supplied Keyverse identifier into identity-mutation authority.

Status: **active PR only**. Protected default branch `develop` does not contain this adapter boundary until the PR is merged.

## Current contract

`KeyverseIdentityDeprovisionReviewPacket` binds only:

- tenant, Person, Employment, and Orgmetra-local identity-binding correlation references;
- SHA-256 identity-binding and employment evidence digests;
- the requesting actor correlation reference;
- the exact reviewed Keyverse revision;
- evidence version and system-recorded UTC time.

Canonical evidence is fixed to:

- `requested_action = deactivate_identity`;
- `purpose_code = employment_identity_deprovisioning`;
- `review_state = requires_human_review`;
- `scope_state = requires_authoritative_employment_and_identity_resolution`;
- `execution_state = not_sent_to_keyverse`;
- `authority_state = not_authorized_to_modify_identity`.

The packet deliberately excludes the Keyverse user ID, username, email, credentials, HR field values, and free-form reason text. Before execution, the host must re-resolve current Employment and the identity binding, obtain the required human confirmation and purpose-bound authority, then use the reviewed Keyverse public contract. This package does not call Keyverse and does not modify an Orgmetra Employment record.

## Read-only owner contract

The reviewed external owner is `ContextualWisdomLab/keyverse@ce207dfd42975db61c82a5963e206fc1db14ac2b`. At that revision, Keyverse's SCIM v2 shim exposes `PATCH /scim/v2/Users/{user_id}` and deactivates the account when `active=false`; SCIM DELETE is also implemented as soft deactivation. Orgmetra treats those as foreign owner behavior, not as a contract it may rewrite.

The standards basis is RFC 7644 (SCIM Protocol) and RFC 7643 (SCIM Core Schema). The adapter does not duplicate Keyverse's identity store or use direct cross-service SQL.

## Integrity

Owned references use canonical namespaced UUIDv4 correlation identifiers; tenant identity accepts the authoritative non-sentinel UUID object contract. Digests are lowercase SHA-256. The reviewed Keyverse revision is exact. System-recorded evidence must be an exact built-in `timezone.utc` datetime that is not in the future. Evidence runtime types fail closed, routine `repr` is redacted, and canonical export checks a process-local construction seal so post-construction rewriting cannot silently alter an existing packet.

A copied packet is a new **non-authorizing** review packet, not proof of review or execution. Durable services must persist it under their normal append-only audit/idempotency constraints.
