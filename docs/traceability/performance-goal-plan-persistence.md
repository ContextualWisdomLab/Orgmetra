# Performance goal-plan persistence traceability

## Truth status

- Protected `develop`: does **not** yet contain authoritative performance-goal persistence.
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
| Activation and human accountability remain bound | activation/authority SHA-256 correlations, approving actor, approval/activation chronology | happy-path persisted state and activation-audit mismatch regression |
| Immutable audit/outbox is mandatory | FK to `audit_event_record` plus required `integration_hub` `outbox_delivery_record` and exact audit semantic checks | focused PostgreSQL persistence regression |
| No rating or employment-decision authority is created | fixed non-authorizing state columns | persisted-state assertion and CHECK constraints |
| Data minimization | no goal text, rating, assessment, compensation, candidate, prompt/model-output columns | prohibited-column regression |
| Tenant isolation | `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, tenant policies | `NOSUPERUSER NOBYPASSRLS` reader visibility regression |
| History cannot be rewritten | immutable anchor; version UPDATE only for database-time closure; DELETE/TRUNCATE rejection | mutation/delete/truncate regressions |
| Stack evidence does not transfer | PR #125 remains dependency-first under #121 | PR metadata and exact-head hosted-run checks |

## Buyer-facing interpretation

After integration, an authorized HR workflow can establish that a particular reviewed plan definition was active for an Employment/Job/cycle and business period, with immutable activation/audit provenance, without reading goal text or implying that Orgmetra has produced a performance rating or employment decision.
