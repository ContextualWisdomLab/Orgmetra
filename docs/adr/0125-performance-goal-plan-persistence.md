# ADR 0125: Persist activated performance-goal plan truth bitemporally

- Status: proposed
- Scope: active PR #125 only; not integrated-`develop` truth
- Parent dependency: PR #121 exact activation boundary

## Context

Orgmetra can govern a reviewed performance-goal plan and can obtain authoritative activation evidence, but an activation receipt is not durable HRIS truth by itself. A commercial HCM system must be able to answer which goal-plan definition applied to one Employment and Job at a business date, what the system knew at a recorded-time cutoff, and which immutable activation/audit evidence authorized that persistence.

Goal text, ratings, assessment scores, compensation values, candidate data, prompts and model output are not necessary to answer that question and would increase privacy and decision-risk surface.

## Decision

Introduce two Orgmetra-owned relations:

1. `performance_goal_plan_record` is the stable tenant-qualified identity for one plan and binds it to one Employment, Job and opaque performance-cycle reference.
2. `performance_goal_plan_version` is the bitemporal fact. It stores goal-set and measurement-definition SHA-256 provenance, goal count, governed feedback cadence, exact value-minimized reviewed-plan and activation evidence bytes plus their SHA-256 digests, authority evidence correlation, accountable approving actor, approval/activation chronology, business-effective interval and system-recorded interval.

The exact plan/activation evidence snapshots are retained because a digest alone does not prove that independently supplied normalized columns describe the evidence that was actually reviewed and activated. Before persistence, Orgmetra recomputes SHA-256 over those exact bytes, enforces the PR #92/#121 v1 key sets and non-authorizing states, and requires tenant, Employment, Job, performance-cycle, goal-set, measurement-definition, cadence, actor, plan-digest, activation, authority and timestamp scope to equal the normalized columns. This closes the checked-evidence-versus-persisted-scope gap while keeping goal text and ratings out of durable evidence.

The database owns `created_at` and `recorded_from` through PostgreSQL transaction time. New recorded intervals start open. Corrections close the current recorded interval and append a replacement; in-place evidence rewrites and DELETE/TRUNCATE fail closed.

Before accepting a version, the database also re-resolves the same-tenant anchor, serializes mutation for that plan, requires complete system-visible `active|leave` Employment coverage and Job-version coverage for the business interval, and verifies an immutable same-tenant audit event plus transactional outbox correlation. The audit event must bind the plan reference, approving actor, activation-evidence digest, purpose `performance_goal_plan_persistence`, reason `activated_goal_plan_record`, result `activated_plan_persisted`, and activation instant.

`persistence_state` is fixed to `authoritatively_persisted`, while `rating_authority_state` and `employment_decision_authority_state` remain respectively `not_authorized_for_performance_rating` and `not_authorized_for_employment_decision`. Persisting a goal plan therefore does not create a rating, compensation, or employment-decision permission.

Both relations use tenant-qualified FORCE RLS. The slice does not query or mutate another CWL service and does not perform cross-service application-table SQL.

## Consequences

This closes the durable-truth gap after PR #121 activation while retaining bitemporal reconstruction and evidence minimization. The focused child evidence is stack-local only: PR #121 must integrate first, then this PR must retarget to fresh `develop` and rerun every applicable local and central gate without transferring predecessor checks or reviews.

The model deliberately does not persist individual goal text. A future content store may hold authorized goal content behind a purpose-bound interface, but this HRIS core remains sufficient to establish which reviewed definition and measurement contract governed a period.

## Primary technical basis

PostgreSQL 18 exclusion constraints are used to prevent overlapping business/system-time truth for the same plan, while row-security policies apply tenant predicates to reads and writes. See the companion doctoring note for dated APA 7 references.
