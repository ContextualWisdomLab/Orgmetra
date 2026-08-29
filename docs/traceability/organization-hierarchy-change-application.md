# Organization hierarchy-change application traceability

## Truth classification

| Capability | State | Evidence owner |
| --- | --- | --- |
| Bitemporal Organization Unit and parent fact | Protected-main truth | `database/migrations/0001_foundation_schema.sql` |
| Human review packet for one proposed parent change | Active parent PR #96 | `organization-hierarchy-change-review` package |
| Authoritative reviewed parent-change application | Active stacked PR #119 | migrations 0027/0028 and dedicated PostgreSQL regressions |
| Protected-main availability of #119 | Not yet true | Requires #96 integration, #119 retarget, migration reconciliation, fresh full gates and repository merge controls |

## Requirement → implementation → verification

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Review evidence alone cannot mutate hierarchy truth | PR #96 packet remains `not_authorized_to_apply`; #119 exposes a separate authoritative DB function whose PUBLIC execution is revoked | untrusted runtime role regression |
| Tenant isolation | tenant-qualified FKs; application table FORCE RLS; same-tenant Organization lookups | Alpha/Beta/no-tenant RLS regression |
| Effective and system-recorded time remain separate | reviewed `effective_on`; PostgreSQL-owned system intervals; correction by predecessor close + preserved/new business-time versions | prior-parent preservation and successor-parent regression |
| Current-parent evidence cannot go stale silently | lock current target version; expected predecessor id/current parent check; recomputed target/hierarchy digests | stale-current-parent regression |
| Graph invariants survive concurrency and future scheduling | tenant-scoped transaction advisory lock plus stale-transaction cutoff guard and effective-time-boundary recursive walk | earlier-transaction/later-commit concurrency regression, sequential cycle check, and future-effective cycle regression |
| Application evidence cannot bind unrelated versions | tenant/unit-qualified predecessor and successor foreign keys; deferred successor reverse-application binding | direct cross-unit predecessor and missing-successor insert regressions |
| Self-parent/cycle/missing parent fail closed | authoritative same-tenant parent resolution and recursive ancestor walk | sequential descendant-as-parent regression; contract checks |
| Human accountability is immutable | requester/reviewer/applier separation; controlled reason; high-impact confirmation; exact review digest; audit/outbox binding | application evidence query plus audit guard |
| Application evidence cannot be rewritten | append-only UPDATE/DELETE guard; TRUNCATE guard | mutation and TRUNCATE regressions |
| PII is minimized | application evidence carries Organization correlations and governance digests/states only | schema review; parent packet flags require no Person/worker/employment-decision data |
| Evidence is deterministic and structurally faithful | exact v1 key shape, JSON type/null checks, fixed `next_action`, SHA-256 review digest, deterministic Organization/hierarchy snapshot digests, and field-for-field application binding | malformed-packet, direct-column-mismatch, dedicated exact-head workflow provenance, and PostgreSQL regressions |

## Concurrency defect and repair provenance

The contract regression deliberately creates an older transaction, then commits a later-started X→Y hierarchy change before the older transaction attempts Y→X. `transaction_timestamp()` is fixed at transaction start, so an application boundary that only serializes on an advisory lock can otherwise evaluate the old graph after acquiring the lock. Migration 0028 rejects any applying transaction when tenant Organization facts were recorded or closed after its recorded cutoff, requiring a fresh retry and preventing both edges from committing into a cycle.

## Integration checklist

#119 remains dependency-first on #96. After #96 actually reaches `develop`, retarget #119 to fresh `develop`, reconcile provisional migration numbers 0027/0028 against the integrated migration ledger, rerun the dedicated application/concurrency lane plus Foundation, Recovery, SAST, Security and other newly applicable product gates at the new exact head, and require the live repository review/ruleset controls. Parent checks, reviews, and stack-local successes are not transferable.
