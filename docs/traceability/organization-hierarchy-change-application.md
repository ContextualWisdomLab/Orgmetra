# Organization hierarchy-change application traceability

## Truth classification

| Capability | State | Evidence owner |
| --- | --- | --- |
| Bitemporal Organization Unit and parent fact | Protected-main truth | `database/migrations/0001_foundation_schema.sql` |
| Human review packet for one proposed parent change | Active parent PR #96 | `organization-hierarchy-change-review` package |
| Authoritative reviewed parent-change application | Active stacked PR #119 | migrations 0027/0028/0029 and dedicated PostgreSQL regressions |
| Protected-main availability of #119 | Not yet true | Requires #96 integration, #119 retarget, migration reconciliation, fresh full gates and repository merge controls |

## Requirement → implementation → verification

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Review evidence alone cannot mutate hierarchy truth | PR #96 packet remains `not_authorized_to_apply`; #119 exposes a separate authoritative DB function whose PUBLIC execution is revoked | untrusted runtime role regression |
| Tenant isolation | tenant-qualified FKs; application table FORCE RLS; same-tenant Organization lookups | Alpha/Beta/no-tenant RLS regression |
| Effective and system-recorded time remain separate | reviewed `effective_on`; PostgreSQL-owned system intervals; correction by predecessor close + preserved/new business-time versions | prior-parent preservation and successor-parent regression |
| Current-parent evidence cannot go stale silently | lock current target version; expected predecessor id/current parent check; recomputed target/hierarchy digests | stale-current-parent regression |
| Graph invariants survive concurrency and future scheduling | tenant-scoped transaction advisory lock plus stale-transaction cutoff guard and effective-time-boundary recursive walk | earlier-transaction/later-commit concurrency regression, sequential cycle check, and future-effective cycle regression |
| A successor cannot outlive valid proposed-parent truth | migration 0029 requires exactly one current-recorded proposed-parent version at every relevant effective boundary within the successor interval | dedicated parent-ending/gap regression plus uninterrupted-parent control |
| Application evidence cannot bind semantically unrelated versions | deferred application validator requires the named predecessor to cover the reviewed `effective_on`, match the reviewed current parent, and be the exact row closed at application time; the named successor must start exactly at `effective_on`, preserve the predecessor business-time end/name/type, use the reviewed proposed parent, be created at the same application timestamp, remain current-recorded, and point back to the exact application | direct-DML historical-predecessor and forged-successor regressions commit deferred constraints and must fail closed |
| Self-parent/cycle/missing parent fail closed | authoritative same-tenant parent resolution and recursive ancestor walk | sequential descendant-as-parent regression; contract checks |
| Hierarchy audit provenance names the owning bounded context and event family | deferred audit validator requires `source=urn:orgmetra:organization_core` and `type=orgmetra.organization.hierarchy_changed` together with exact subject, actor, purpose, reason, evidence digest, result, high-impact marker, human confirmation, and outbox link | persisted canonical event assertion plus direct-DML wrong-source and wrong-type regressions |
| Human accountability is immutable | requester/reviewer/applier separation; controlled reason; high-impact confirmation; exact review digest; audit/outbox binding | application evidence query plus audit guard |
| Application evidence cannot be rewritten | append-only UPDATE/DELETE guard; TRUNCATE guard | mutation and TRUNCATE regressions |
| PII is minimized | application evidence carries Organization correlations and governance digests/states only | schema review; parent packet flags require no Person/worker/employment-decision data |
| Evidence is deterministic and structurally faithful | exact v1 key shape, JSON type/null checks, fixed `next_action`, SHA-256 review digest, deterministic Organization/hierarchy snapshot digests, and field-for-field application binding | malformed-packet, direct-column-mismatch, dedicated exact-head workflow provenance, and PostgreSQL regressions |

## Concurrency defect and repair provenance

The contract regression deliberately creates an older transaction, then commits a later-started X→Y hierarchy change before the older transaction attempts Y→X. `transaction_timestamp()` is fixed at transaction start, so an application boundary that only serializes on an advisory lock can otherwise evaluate the old graph after acquiring the lock. Migration 0028 rejects any applying transaction when tenant Organization facts were recorded or closed after its recorded cutoff, requiring a fresh retry and preventing both edges from committing into a cycle.

## Future-parent continuity and event-owner defect provenance

Review evidence can validly reference a proposed parent at `effective_on` while that parent's current-recorded version ends later inside the child successor interval. The earlier recursive cycle walk used an inner join, so an effective boundary with no visible parent version disappeared from `parent_path`; a dangling future relationship could therefore survive cycle validation. The regression introduced before migration 0029 creates a parent that ends on 2026-10-01 and does not resume until 2026-11-01 while a child is proposed under it from 2026-09-15. Migration 0029 evaluates all effective boundaries and rejects any coordinate with a proposed-parent visible-version count other than one. The same regression then exercises a valid uninterrupted-parent control and requires persisted hierarchy audit evidence to identify `organization_core`, preventing the previous `people_api` source misattribution.

## Evidence-semantic forgery defect provenance

Tenant/unit foreign keys and a successor back-reference are necessary but do not prove that the referenced versions are the bitemporal correction a human reviewed. A same-unit historical predecessor can satisfy those structural keys while not covering `effective_on`; likewise, a same-unit successor can point back to the application while starting on the wrong business date or silently changing the unit name/type. A table-capable maintenance path could also attach a well-formed audit/outbox pair whose CloudEvent source or type belongs to another bounded context/event family. The dedicated regression now bypasses the authoritative function deliberately, constructs each of those structurally valid but semantically false records, and commits the deferred constraints. Migration 0029 rejects them by binding predecessor, successor, audit event, and outbox semantics to the exact reviewed correction coordinate and application transaction. This is defense against direct-DML evidence forgery; deployment privileges must still deny routine roles direct writes to the underlying evidence and hierarchy tables.

## Integration checklist

#119 remains dependency-first on #96. After #96 actually reaches `develop`, retarget #119 to fresh `develop`, reconcile provisional migration numbers 0027/0028/0029 against the integrated migration ledger, rerun the dedicated application/concurrency/parent-continuity lane plus Foundation, Recovery, SAST, Security and other newly applicable product gates at the new exact head, and require the live repository review/ruleset controls. Parent checks, reviews, and stack-local successes are not transferable.
