# Position reporting persistence traceability

## Truth status

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has no persisted Position-to-Position reporting relation.
- **Parent active PR:** #94 adds bitemporal in-memory reporting reconstruction at `3f67182bb3065f2fc8fd974bfdd75a390d8a8fdc`.
- **This active PR:** #106 persists reviewed solid-line Position relationships and remains a Draft stacked descendant until #94 integrates and this branch is retargeted/revalidated.
- **Separate active owner:** #95 owns the in-memory pre-mutation review packet. #106 consumes only the reviewed-evidence digest plus immutable application audit correlation and does not rewrite #95.

## Requirement → implementation → executable evidence

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Position-to-Position, never Person-to-Person | `position_reporting_relationship_record.subordinate_position_record_id` and version `manager_position_record_id`; no Person/Assignment columns | `tests/test_position_reporting_persistence_postgres.sh` valid insert and schema contract |
| One durable solid-line identity per subordinate | unique `(tenant_record_id, subordinate_position_record_id, relationship_type_code)` anchor | valid insert plus duplicate-anchor failure supplied by database unique constraint |
| Effective/business and recorded/system time remain separate | version `effective_from/effective_to`; anchor/version `recorded_from/recorded_to` | backdated-system-time regression; bitemporal exclusion |
| System-recorded time is database-owned | `enforce_position_reporting_system_time()` requires `recorded_from = transaction_timestamp()` and open `recorded_to` | caller-backdated anchor regression |
| Same-tenant subordinate and manager | composite FKs to `position_record(tenant_record_id, position_record_id)` plus FORCE RLS | schema FK and non-bypass tenant reader regression |
| Both endpoints are staffable for the full reporting interval | `position_reporting_has_staffable_coverage(...)` resolves system-visible Position anchors and uses `range_agg(daterange(...))` over same-tenant `active`/`open` PositionVersion rows; the resulting multirange must contain the entire reporting effective range | regression first attempts persistence before any PositionVersion exists and requires `staffable PositionVersion coverage`; valid fixture succeeds only after active/open endpoint versions are inserted |
| No self-reporting | `enforce_position_reporting_scope()` | self-report PostgreSQL regression |
| No effective-time management cycle in one session | recursive effective-period intersection in `enforce_position_reporting_scope()` | A→B then B→A PostgreSQL regression |
| Concurrent opposite graph mutations cannot both commit | transaction-scoped tenant advisory lock is acquired before the VOLATILE trigger's graph queries | `tests/test_position_reporting_concurrency_postgres.sh` holds X→Y open while Y→X races; exactly one edge may commit |
| Human review is distinct from applying actor | exact actor-format checks plus `reviewer_actor_reference <> applied_by_actor_reference` | database constraints and valid separated actors fixture |
| Reviewed evidence is immutable application evidence, not an unattested column | application audit `orgmetraevidence` must equal `review_evidence_digest_sha256`; stored application digest must equal `audit_event_record.event_envelope_digest` | `tests/test_position_reporting_review_binding_postgres.sh` |
| Applied truth requires immutable audit/outbox evidence with the governed reason | scope guard verifies purpose `position_reporting_change_apply`, reason `approved_reporting_line_change`, applying actor, reviewed-evidence digest, exact audit-envelope digest, subject, result code, review/application chronology, and integration-hub outbox | valid `record_audit_outbox_event(...)` fixture plus wrong-reason regression in `tests/test_position_reporting_persistence_postgres.sh`; mismatched evidence fails closed |
| Historical truth cannot be rewritten/deleted | `protect_position_reporting_history()` | manager rewrite regression |
| Table-wide destruction cannot bypass row guards | explicit BEFORE TRUNCATE guards and revoked PUBLIC TRUNCATE | TRUNCATE regression |
| Tenant isolation is enforced for ordinary app/read roles | `ENABLE` + `FORCE ROW LEVEL SECURITY`; tenant policy on both relations | `NOSUPERUSER NOBYPASSRLS` reader sees alpha=1, beta=0, missing-context=0 |
| Exact candidate execution | dedicated workflow checks out `${{ github.event.pull_request.head.sha }}` | `.github/workflows/position-reporting-persistence-quality.yml` |

## Non-goals and buyer-safe interpretation

Persisted reporting hierarchy describes Position structure. It does not prove which worker occupies a seat, does not create/modify Assignment, does not imply performance/compensation authority, and is not an employment decision. PR #94 remains the descriptive snapshot contract for staffable endpoint interpretation at a requested bitemporal coordinate; #106 now rejects persistence that could not satisfy that staffable Position contract across the relationship's own effective interval.

The database relation is authoritative only after the application boundary supplies valid reviewed application evidence. RLS does not replace purpose-bound authorization. Production roles must remain non-superuser and `NOBYPASSRLS`; application mutation authority, API exposure, accessible organization-chart UI, migration/rollback choreography, and release integration remain separate bounded work.
