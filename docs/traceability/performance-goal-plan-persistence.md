# Performance goal-plan persistence traceability

## Truth status

- Integrated `develop`: does **not** yet contain authoritative performance-goal persistence.
- Parent PR #92: governed human-reviewed plan evidence.
- Parent PR #121: authoritative activation receipt; dependency for this slice.
- Active PR #125: durable bitemporal persistence described here.
- Out of scope: goal text storage, ratings, compensation decisions, employment decisions, autonomous LLM decisions, foreign-service mutations, release/tag operations.

## Requirement → implementation → evidence

| Requirement | Implementation | Executable evidence |
| --- | --- | --- |
| Stable tenant-qualified plan identity | `performance_goal_plan_record` | happy-path insert and tenant RLS regression |
| Separate business and system time | `effective_from/effective_to` plus database-owned `recorded_from/recorded_to` | backdated recorded-time rejection and correction-not-rewrite regression |
| Employment/Job scope must remain authoritative for the entire plan period | `performance_goal_plan_employment_has_coverage(...)`, `performance_goal_plan_job_has_coverage(...)` | non-covered Employment and Job interval regressions |
| One simultaneous truth for a plan coordinate | GiST bitemporal exclusion constraint | PostgreSQL schema constraint plus focused persistence gate |
| Exact reviewed plan must equal normalized persisted scope | `plan_evidence_json`, recomputed SHA-256, exact v1 key set, tenant/Employment/Job/cycle/goal/measurement/cadence/reviewer/time equality | forged normalized goal-set regression with otherwise unchanged exact plan evidence |
| Exact activation must bind the same plan and authority | `activation_evidence_json`, recomputed SHA-256, exact v1 key set, plan digest/activation/authority/actor/timestamp equality | happy-path evidence binding plus activation/audit mismatch regression |
| Immutable audit/outbox is mandatory | FK to `audit_event_record` plus required `integration_hub` `outbox_delivery_record` and exact audit semantic checks | focused PostgreSQL persistence regression |
| No rating or employment-decision authority is created | fixed non-authorizing state columns and exact parent evidence-state checks | persisted-state assertion and CHECK/evidence-binding constraints |
| Data minimization | exact parent evidence excludes goal text/rating/assessment/compensation/candidate/model output; no such normalized columns are introduced | prohibited-column regression plus exact evidence key-set validation |
| Tenant isolation | `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, tenant policies | `NOSUPERUSER NOBYPASSRLS` reader visibility regression |
| History cannot be rewritten | immutable anchor; version UPDATE only for database-time closure; DELETE/TRUNCATE rejection | mutation/delete/truncate regressions |
| Stack evidence does not transfer | PR #125 remains dependency-first under #121 | PR metadata and exact-head hosted-run checks |

## Buyer-facing interpretation

After integration, an authorized HR workflow can establish that a particular reviewed plan definition was active for an Employment/Job/cycle and business period, with immutable activation/audit provenance, without reading goal text or implying that Orgmetra has produced a performance rating or employment decision.
