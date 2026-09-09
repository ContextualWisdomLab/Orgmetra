# Organization Hierarchy Change Review

This package records **human review evidence before an Organization Unit parent relationship is changed**. It does not update the HRIS hierarchy itself.

## Why this boundary exists

Moving an Organization Unit under a different parent can change reporting scope, access scope, workforce analytics, downstream approvals, and the interpretation of historical organization structure. A caller therefore must not turn a reviewed request directly into a mutation.

`OrganizationHierarchyChangeReviewPacket` binds the reviewed change to:

- one tenant and one Organization Unit;
- the reviewed current parent and proposed parent, where `None` represents a real root transition rather than a sentinel identifier;
- a business-effective date that remains separate from the system-recorded evidence timestamp;
- exact Organization Unit and hierarchy snapshot SHA-256 evidence;
- a controlled purpose and reason;
- distinct accountable requester and reviewer correlations; and
- an explicit evidence version.

The packet deliberately excludes Person PII, worker values, compensation, ratings, free-form personal text, and employment-decision authority.

## What it does not authorize

Every packet remains:

- `requires_human_review`;
- `requires_authoritative_resolution`;
- `not_authorized_to_apply`; and
- `human_review_only`.

Before any later mutation, the authoritative Orgmetra HRIS boundary must re-resolve the Organization Unit, current parent, proposed parent, and hierarchy at the requested business date and current system-recorded cutoff. It must prove same-tenant scope, reject stale current-parent evidence, self-parenting, cycles, and multiple visible parents, re-establish accountable actor separation, verify the reviewed digests/reason, and commit immutable audit/outbox evidence atomically with the mutation.

## Identifier and evidence rules

HRIS-owned tenant and Organization Unit identifiers accept canonical non-sentinel operational UUID text, including UUIDv7, so this package does not freeze the core identifier version. Packet-owned change references and actor correlations are UUIDv4. Lowercase SHA-256 digests bind evidence without copying the source records themselves.

Caller-defined packet classes are rejected when subclass creation is attempted, before a subclass can replace `__post_init__`, `__getattribute__`, or another validation/emission hook. Caller-defined subclasses of trust-bearing strings, integers, dates, or datetimes are likewise rejected at issuance. Issuance captures every trust-bearing field once, applies the complete semantic contract to that one snapshot, canonicalizes only those captured values, and derives both the creation digest and live-reference key from the same snapshot. A low-level mutation after one semantic check has run therefore cannot become silently sealed as reviewed evidence; if the retained live object changes after issuance snapshot capture, later canonical export rejects that changed live state against the creation digest.

Issuance is single-use for one live packet object. The process-local registry reserves an object before semantic validation begins; a direct or concurrent second `__post_init__()` call fails closed if that object is already issuing or has already been issued. This prevents low-level mutation to a fresh valid hierarchy-change reference from turning one issued object into a second issuance. Independent packet objects remain concurrent, and failed first-time validation releases the reservation.

Canonical export separately reads every trust-bearing field once into a local snapshot, validates the exact built-in runtime types on that same snapshot, and serializes only those captured values. A caller-defined `str` or `int` subtype observed before export snapshot capture therefore fails closed even if its JSON value and SHA-256 bytes are representation-preserving; a low-level mutation that occurs after capture cannot change the payload already selected for that export. The issuance digest separately rejects semantic value changes on a later export. Canonical evidence is deterministic and the routine `repr` is redacted.

`recorded_at` is system-recorded issuance evidence: construction rejects a timestamp that is later than the current UTC time. That freshness check is deliberately issuance-only. Later canonical export rechecks the exact built-in timestamp shape of the captured snapshot and the creation digest without consulting the wall clock, so a backward clock adjustment cannot invalidate evidence that was validly issued.

A tenant-qualified `organization_hierarchy_change_reference` is also bound to one evidence digest while any idempotent packet carrying that reference remains alive in the process. An exact duplicate is allowed; a different reason, parent, timestamp, digest, actor, or other trust-bearing value under the same still-live reference fails closed. This prevents `dataclasses.replace()` or a second constructor call from silently minting conflicting live review evidence under one packet correlation.

The in-process creation seal, single-use issuance reservation, and live-reference binding are defense in depth only. They are not durable database uniqueness, distributed authorization, restart-stable identity, or a substitute for the authoritative audit/outbox transaction. Durable persistence must enforce tenant-qualified uniqueness and immutable evidence independently.

## Quality contract

Canonical Foundation CI builds one exact wheel, binds its SHA-256 at install time, executes tests against the installed artifact on CPython 3.14.7, requires exact 100% owned statement and branch coverage, and proves the checkout is clean. The retired repository-owned feature workflow must not be resurrected. Recovery, SAST, security, and other centrally required workflows remain separate exact-head evidence.
