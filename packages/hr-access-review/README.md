# Orgmetra HR Access Review

This package creates a **value-minimized review artifact for existing HR access**. It helps an accountable reviewer record whether an existing access snapshot should be retained, reduced, or removed without turning that review artifact into an access-control command.

## What the packet records

`HrAccessReviewPacket` binds:

- the authoritative Orgmetra tenant;
- one opaque `access_review:` reference;
- the reviewed subject, requester, and independent reviewer as packet-local pseudonymous `actor:` UUIDv4 correlations;
- SHA-256 evidence for the reviewed resource scope, authorization policy, entitlement snapshot, and reviewer identity-resolution evidence;
- the fixed governance purpose `hr_access_recertification`, a bounded review reason, and a non-expanding recommendation;
- the human review instant and a distinct later-or-equal system-recorded instant, both as exact UTC evidence;
- a bounded positive evidence version.

The packet does **not** contain HR field values, passwords, tokens, raw entitlement lists, free-form reviewer notes, credentials, names, employee numbers, or raw identity-provider subject identifiers. Its representation is redacted.

The packet-local `actor:` UUIDv4 values are **not a Keyverse identifier contract** and are not authentication evidence. The Orgmetra host must derive or allocate these pseudonymous correlations only after resolving the live identity through the approved identity boundary, and must keep the identity-resolution evidence independently bound by digest. This deliberately avoids imposing UUID semantics on a foreign identity provider while preventing direct person identifiers from being copied into durable access-review evidence.

## What the packet cannot do

The canonical evidence always states `not_authorized_to_modify_access` and `requires_authoritative_resolution`. A `retain_existing_access`, `reduce_existing_access`, or `remove_existing_access` recommendation is review evidence only. It does not grant, revoke, or alter a permission.

Before enforcing any recommendation, the host must re-resolve the exact tenant, subject, current resource scope, purpose, authorization policy, entitlement state, reviewer identity evidence, and accountable reviewer through the authoritative identity/authorization boundary. Any resulting mutation must enter its own purpose-bound authorization and immutable audit/outbox path.

## Review time and system-recorded time

`reviewed_at` records when the accountable human review occurred. `recorded_at` records when that evidence entered the Orgmetra evidence boundary and may not precede the human review. Keeping the two timestamps distinct prevents a later system record from silently masquerading as an earlier review event. The packet still does not claim that an application-supplied time is durable database transaction time; durable system-recorded truth begins when the verified canonical evidence enters Orgmetra's immutable audit/outbox persistence boundary.

## Independence and evidence integrity

The reviewer must differ from both the requester and the reviewed subject. A reviewer identity-evidence digest is bound alongside the packet-local reviewer correlation so the review event is not represented by a bare actor label alone. Trust-bearing text uses exact built-in runtime primitives before parsing, membership tests, equality, or serialization. Canonical export revalidates the live packet and compares it with a process-local creation digest so a rewritten frozen object or an unregistered shallow copy fails closed.

The process-local digest is in-process tamper evidence, not durable non-repudiation. Durable evidence begins only after the verified canonical document enters Orgmetra's immutable audit/outbox boundary.

## Review frequency

This package deliberately does not hard-code annual, quarterly, or another review interval. NIST SP 800-53 Rev. 5 AC-2 leaves the account-review frequency to the organization. Orgmetra records the reviewed evidence and reason while policy owners remain responsible for choosing and enforcing the appropriate cadence.

## Developer check

The dedicated `HR Access Review Quality` workflow executes the package tests on the exact pull-request head, builds and installs the package artifact outside the source tree, and requires exactly 100% owned statement and branch coverage plus a clean checkout.
