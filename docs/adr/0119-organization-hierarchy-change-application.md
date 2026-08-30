# ADR 0119: Governed Organization hierarchy-change application

- Status: Proposed
- Parent: PR #96 `feat/organization-hierarchy-change-review`
- Protected-main truth at branch creation: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not yet contain PR #96 or this application boundary.
- Integration rule: #96 must integrate first. PR #119 must then be retargeted to fresh `develop`, migration numbering reconciled, and all applicable exact-head gates rerun without transferring parent evidence.

## Decision

Orgmetra will apply a reviewed Organization Unit parent change only through an authoritative, tenant-scoped bitemporal database boundary. The pre-mutation packet from PR #96 remains non-authorizing evidence. The application boundary must independently re-resolve the target Organization Unit, its current parent, the proposed parent, and the tenant hierarchy at the requested business-effective date and a system-recorded cutoff before it writes HRIS truth.

The application transaction:

1. requires operational tenant/unit/application/audit/outbox identities and pseudonymous requester, reviewer, and applier correlations;
2. keeps requester/reviewer and reviewer/applier distinct; requester and applier may be the same actor because the independent reviewer is the segregation-of-duties boundary;
3. takes one tenant-scoped transaction-level advisory lock before graph validation so authoritative hierarchy changes that use this boundary serialize;
4. rejects a transaction whose system-time cutoff predates a hierarchy fact committed after that transaction began, requiring a retry rather than allowing stale pre-lock truth to commit;
5. verifies exact v1 value-minimized review evidence, its SHA-256 digest, reason, reviewed current parent, and independently recomputed target-unit and whole-hierarchy snapshot digests;
6. fails closed on missing/ambiguous same-tenant truth, stale current-parent evidence, self-parenting, missing proposed parents, a proposed-parent effective-time gap anywhere in the successor interval, or cycles at every relevant effective-time boundary;
7. records high-impact human-confirmed audit/outbox evidence in the same transaction and identifies the producing bounded context as `urn:orgmetra:organization_core` and the event family as `orgmetra.organization.hierarchy_changed`;
8. closes only the predecessor system-recorded interval, preserves earlier business-time truth when the change is future-effective, and inserts the reviewed successor parent fact;
9. stores no Person, worker, compensation, rating, candidate, free-form HR, prompt, model-output, or credential values in application evidence;
10. forces tenant RLS on application evidence, makes that evidence append-only, rejects TRUNCATE, and revokes routine PUBLIC execution of the authoritative mutation function.

Migration 0029 is an active-PR hardening migration, not protected-main truth. It replaces the application function without changing its public signature. Its continuity check evaluates every effective boundary already used by graph validation and requires exactly one current-recorded proposed-parent version at each coordinate within the successor interval. This prevents a relationship from remaining effective while its parent has no corresponding valid OrganizationUnitVersion. It also binds the deferred application evidence to the exact reviewed bitemporal correction: the named predecessor must cover `effective_on`, match the reviewed current parent, and be the row closed at the application timestamp; the named successor must begin at `effective_on`, preserve the predecessor's business-time end, unit name, and organization type, use the reviewed proposed parent, be created at the application timestamp, remain current-recorded, and point back to the exact application. The same deferred boundary requires the hierarchy CloudEvent to use both the `organization_core` source and `organization.hierarchy_changed` event type, preventing structurally valid evidence from being attached to an unrelated event family.

## Why a transaction-level advisory lock is necessary but not sufficient

Organization parent changes are graph mutations. Two individually valid edges can form a cycle when evaluated concurrently. PostgreSQL transaction-level advisory locks provide an application-defined exclusive lock that is automatically released at transaction end, which is appropriate for serializing the Orgmetra-owned hierarchy mutation boundary. Advisory locks are voluntary, so they do not replace RLS, database privileges, foreign keys, exclusion constraints, or immutable audit evidence.

`transaction_timestamp()` is fixed at transaction start. An older transaction can therefore begin before a later hierarchy change, acquire the advisory lock only after that later change commits, and otherwise reconstruct the earlier hierarchy at its older cutoff. Under the default `READ COMMITTED` isolation, the concurrency-hardening trigger detects tenant Organization facts whose `recorded_from` or `recorded_to` is later than the applying transaction's recorded time and raises a serialization failure. Under `REPEATABLE READ` or `SERIALIZABLE`, the transaction snapshot may not see that later commit, so PostgreSQL's concurrent-update or serializable-conflict detection remains the second fail-closed boundary. Callers must retry any `40001` result from a fresh transaction. The trigger intentionally checks the whole tenant rather than only the proposed path; unrelated concurrent hierarchy changes conservatively require the same retry.

## Bitemporal semantics

`effective_on` is business time. `recorded_at`/`recorded_from`/`recorded_to` are system-recorded time owned by PostgreSQL. A reparenting never rewrites prior history. If the predecessor was effective before `effective_on`, the application closes its system interval, writes a preserved successor representing the prior parent through `effective_on`, and writes the new parent from `effective_on` onward. This keeps business-time correction separate from system-recorded history.

A proposed parent must itself have continuous current-recorded business-time truth for every effective coordinate covered by the new child-parent fact. An ending parent version without an immediately visible replacement, including a gap before a later scheduled replacement, invalidates the application. The whole transaction fails before durable hierarchy truth is committed.

Structural identity alone is not sufficient bitemporal evidence. Tenant/unit-qualified foreign keys can prove that a referenced predecessor or successor belongs to the same Organization Unit while still allowing a historical predecessor outside `effective_on`, or a successor whose effective interval or descriptive unit attributes do not describe the reviewed correction. Deferred semantic validation therefore checks both version identities against the exact application coordinate and transaction time before commit.

## Security and privacy consequences

The application relation is governance evidence, not a copy of HR data. FORCE RLS and tenant-qualified foreign keys constrain row scope. Predecessor and successor version references are tenant/unit-qualified; the successor reference is deferred so the application row can be inserted before the new version, while a deferred trigger requires that version to point back to the exact application record and verifies the predecessor/successor business-time and system-time semantics described above. The reviewed JSON is type-checked, null-safe, and bound field-for-field to the application row. A future-effective change is checked across every effective-time boundary in the successor interval, so a later scheduled edge cannot close a cycle unnoticed and a future parent gap cannot create a dangling business-time relationship. The authoritative function is not granted to `PUBLIC`; a deployment must grant it only to the intended Orgmetra mutation role. High-impact audit evidence binds actor, purpose, controlled reason, reviewed evidence digest, human confirmation, subject, result, bounded-context source, event type, and outbox delivery atomically.

The deferred validators intentionally defend against table-capable maintenance paths that could otherwise create structurally valid but semantically false application/audit records. They do not replace least-privilege deployment grants: routine application roles must still be denied direct writes to hierarchy versions, application evidence, audit records, and outbox records and must use the governed mutation boundary.

This ADR does not claim certification, release readiness, or protected-main integration. It is active-PR architecture until #119 is integrated and revalidated on the final protected head.
