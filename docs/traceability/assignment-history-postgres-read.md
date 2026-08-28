# Assignment-history PostgreSQL read traceability

## Status

Active stacked PR #148 only. This document does not claim protected-`develop` integration. Parent #142 remains the purpose-bound API contract and must integrate first.

## Buyer problem

PR #142 closes the P1 service-contract gap for **Employee profile with bitemporal assignment history**, but intentionally leaves persistence injected. Without a canonical adapter, an Orgmetra deployment still needs bespoke host code to obtain that history from the normalized `assignment_record` relation.

## Parent authority consumed

- `services/people-api/src/orgmetra_people_api/assignment_history.py` defines `AssignmentHistoryReadPort`, `AssignmentHistoryRecord`, purpose-bound authorization-before-read, field minimization, business/system-time separation, and post-persistence service revalidation.
- `database/migrations/0001_foundation_schema.sql` owns canonical `assignment_record` identity, Person/Employment/Position relationships, allocation, effective/business time, recorded/system time, bitemporal mutation guard, and tenant RLS contract.
- Parent #142 exact head at child creation: `d832006843111cc03751ec2bcd532df916bbc1e2`.

## Test-first evidence

Contract-only child head `55a287fe77631bfe9aa5c51d00f737431d3bc64c` contained the focused quality workflow and realistic adapter regressions while production `orgmetra_people_api.postgres_assignment_history` was absent.

Hosted **Assignment History PostgreSQL Read Quality** run `33198039662`, job `98940130089`, checked out and proved that exact SHA, installed the reviewed Python 3.14 toolchain, compiled the existing People boundary, and then failed during focused test collection with:

`ModuleNotFoundError: No module named 'orgmetra_people_api.postgres_assignment_history'`

This is the intended RED at the first Orgmetra-owned boundary. No predecessor/parent failure is being relabeled as RED evidence.

## Active implementation mapping

| Requirement | Production boundary | Regression |
| --- | --- | --- |
| No DB access on invalid target | exact tenant/person operational UUID and built-in UTC `known_at` validation before `connection_factory()` | parameterized invalid UUID/time cases assert zero connection calls |
| Database cannot mutate HR truth | `SET TRANSACTION ISOLATION LEVEL READ COMMITTED, READ ONLY` | SQL execution-order assertion |
| Existing forced RLS receives tenant context | transaction-local `pg_catalog.set_config('orgmetra.tenant_record_id', ..., true)` before SELECT | SQL execution-order and exact-parameter assertion |
| Explicit target scope | SELECT from `public.assignment_record` with exact tenant and person predicates | SQL contract assertions |
| Preserve system-knowledge semantics | `recorded_from <= known_at` and `(recorded_to IS NULL OR known_at < recorded_to)` | SQL contract plus future/closed-at-cutoff adversarial rows |
| Preserve full business history | no effective-date WHERE predicate; deterministic `effective_from, assignment_record_id` ordering | SQL contract and returned typed record assertions |
| Deterministic driver-independent UTC | PostgreSQL projects timestamps with `AT TIME ZONE 'UTC'`; adapter accepts only exact naive DB datetimes before attaching built-in UTC | aware/non-datetime DB timestamp regressions |
| Untrusted DB-API boundary | exact list result, exact tuple row shape, parent record integrity reconstruction | malformed container/row/value regressions |
| Defense-in-depth target check | reconstructed tenant/person must equal request even after SQL/RLS | foreign tenant/person row regressions |
| Immutable typed result | adapter returns tuple of `AssignmentHistoryRecord` | empty and non-empty result regressions |
| Public integration | `PostgresAssignmentHistoryReadPort` exported from People API package root | package export in active child |

## Privacy and authority boundary

The adapter does not accept a purpose code or authorization decision because it is not a disclosure boundary. The parent service authorizes first, then calls this adapter, then independently revalidates persistence evidence and emits only authorized fields. The adapter does not join names, contacts, compensation, assessments, ratings, candidate records, credentials, prompts, or model output. It performs no mutation, audit/outbox write, high-impact decision, or foreign-service call.

## Merge evidence rule

Only exact-current-head child evidence is applicable to #148. The RED head above proves the owning boundary only. Parent #142 checks/reviews and any predecessor child checks do not transfer. After #142 integrates, retarget #148 to fresh protected `develop`, reconcile parent/base changes, then rerun every applicable focused/People/Foundation/SAST/Security/Recovery/central gate before review readiness.
