# ADR 0119: Governed Organization hierarchy-change application

- Status: proposed in active stacked PR #119
- Parent: PR #96 `feat/organization-hierarchy-change-review`
- Protected-main truth at branch creation: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not yet contain PR #96 or this application boundary.
- Integration rule: #96 must integrate first. PR #119 must then be retargeted to fresh `develop`, migration numbering reconciled, and all applicable exact-head gates rerun without transferring parent evidence.

## Decision

Orgmetra will apply a reviewed Organization Unit parent change only through an authoritative, tenant-scoped bitemporal database boundary. The pre-mutation packet from PR #96 remains non-authorizing evidence. The application boundary must independently re-resolve the target Organization Unit, its current parent, the proposed parent, and the tenant hierarchy at the requested business-effective date and a system-recorded cutoff before it writes HRIS truth.

The application transaction:

1. requires operational tenant/unit/application/audit/outbox identities and pseudonymous requester, reviewer, and applier correlations;
2. keeps requester/reviewer and reviewer/applier distinct;
3. takes one tenant-scoped transaction-level advisory lock before graph validation so authoritative hierarchy changes that use this boundary serialize;
4. rejects a transaction whose system-time cutoff predates a hierarchy fact committed after that transaction began, requiring a retry rather than allowing stale pre-lock truth to commit;
5. verifies exact v1 value-minimized review evidence, its SHA-256 digest, reason, reviewed current parent, and independently recomputed target-unit and whole-hierarchy snapshot digests;
6. fails closed on missing/ambiguous same-tenant truth, stale current-parent evidence, self-parenting, missing proposed parents, or cycles;
7. records high-impact human-confirmed audit/outbox evidence in the same transaction;
8. closes only the predecessor system-recorded interval, preserves earlier business-time truth when the change is future-effective, and inserts the reviewed successor parent fact;
9. stores no Person, worker, compensation, rating, candidate, free-form HR, prompt, model-output, or credential values in application evidence;
10. forces tenant RLS on application evidence, makes that evidence append-only, rejects TRUNCATE, and revokes routine PUBLIC execution of the authoritative mutation function.

## Why a transaction-level advisory lock is necessary but not sufficient

Organization parent changes are graph mutations. Two individually valid edges can form a cycle when evaluated concurrently. PostgreSQL transaction-level advisory locks provide an application-defined exclusive lock that is automatically released at transaction end, which is appropriate for serializing the Orgmetra-owned hierarchy mutation boundary. Advisory locks are voluntary, so they do not replace RLS, database privileges, foreign keys, exclusion constraints, or immutable audit evidence.

`transaction_timestamp()` is fixed at transaction start. An older transaction can therefore begin before a later hierarchy change, acquire the advisory lock only after that later change commits, and otherwise reconstruct the earlier hierarchy at its older cutoff. The concurrency-hardening trigger detects tenant Organization facts whose `recorded_from` or `recorded_to` is later than the applying transaction's recorded time and raises a serialization failure so the caller must retry from a fresh transaction.

## Bitemporal semantics

`effective_on` is business time. `recorded_at`/`recorded_from`/`recorded_to` are system-recorded time owned by PostgreSQL. A reparenting never rewrites prior history. If the predecessor was effective before `effective_on`, the application closes its system interval, writes a preserved successor representing the prior parent through `effective_on`, and writes the new parent from `effective_on` onward. This keeps business-time correction separate from system-recorded history.

## Security and privacy consequences

The application relation is governance evidence, not a copy of HR data. FORCE RLS and tenant-qualified foreign keys constrain row scope. The authoritative function is not granted to `PUBLIC`; a deployment must grant it only to the intended Orgmetra mutation role. High-impact audit evidence binds actor, purpose, controlled reason, reviewed evidence digest, human confirmation, subject, result, and outbox delivery atomically.

This ADR does not claim certification, release readiness, or protected-main integration. It is active-PR architecture until #119 is integrated and revalidated on the final protected head.
