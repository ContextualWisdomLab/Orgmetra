# Orgmetra HR Access Review

This package creates a **value-minimized review artifact for existing HR access**. It helps an accountable reviewer record whether an existing access snapshot should be retained, reduced, or removed without turning that review artifact into an access-control command.

## What the packet records

`HrAccessReviewPacket` binds:

- the authoritative Orgmetra tenant;
- one opaque `access_review:` reference;
- the reviewed subject, requester, and independent reviewer as opaque `actor:` references;
- SHA-256 evidence for the reviewed resource scope, authorization policy, and entitlement snapshot;
- a bounded review reason and a non-expanding recommendation;
- an exact UTC review time and evidence version.

The packet does **not** contain HR field values, passwords, tokens, raw entitlement lists, free-form reviewer notes, or credentials. Its representation is redacted.

## What the packet cannot do

The canonical evidence always states `not_authorized_to_modify_access` and `requires_authoritative_resolution`. A `retain_existing_access`, `reduce_existing_access`, or `remove_existing_access` recommendation is review evidence only. It does not grant, revoke, or alter a permission.

Before enforcing any recommendation, the host must re-resolve the exact tenant, subject, current resource scope, purpose, authorization policy, entitlement state, and accountable reviewer through the authoritative identity/authorization boundary. Any resulting mutation must enter its own purpose-bound authorization and immutable audit/outbox path.

## Independence and evidence integrity

The reviewer must differ from both the requester and the reviewed subject. Trust-bearing text uses exact built-in runtime primitives before parsing, membership tests, equality, or serialization. Canonical export revalidates the live packet and compares it with a process-local creation digest so a rewritten frozen object or an unregistered shallow copy fails closed.

The process-local digest is in-process tamper evidence, not durable non-repudiation. Durable evidence begins only after the verified canonical document enters Orgmetra's immutable audit/outbox boundary.

## Review frequency

This package deliberately does not hard-code annual, quarterly, or another review interval. NIST SP 800-53 Rev. 5 AC-2 leaves the account-review frequency to the organization. Orgmetra records the reviewed evidence and reason while policy owners remain responsible for choosing and enforcing the appropriate cadence.

## Developer check

The dedicated `HR Access Review Quality` workflow executes the package tests on the exact pull-request head and requires exactly 100% owned statement and branch coverage plus a clean checkout.
