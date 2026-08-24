# Job qualification-rule persistence traceability

## State

- Protected-main truth: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` stores Job Analysis snapshot/Task/KSAO evidence but has no normalized durable qualification-rule persistence relation.
- Dependency active PR: #104 `feat/job-qualification-rule-review@d92ac4cb798b3bd32b632c0ab677c03f944070e4` adds the human-reviewed, non-authorizing proposal evidence.
- This active stacked PR: `feat/job-qualification-rule-persistence` adds durable normalized persistence only after that review boundary.
- Planned: separate authoritative activation/use boundary for recruiting or selection. This PR does not activate rules or evaluate people.

## Requirement mapping

| Requirement | Owned boundary | Evidence |
|---|---|---|
| PRD FR-004 stores qualification rules | `job_qualification_rule_record`, `job_qualification_rule_version` | `tests/test_job_qualification_rule_persistence_postgres.sh` |
| Preserve Job / Job Analysis provenance | version INSERT scope trigger | same-Job validated snapshot + exact snapshot digest regressions |
| Preserve Task/KSAO/source evidence | SHA-256 linkage columns | lower-case digest constraints and exact canonical review evidence |
| Human review without autonomous decision authority | reviewer/evidence version + fixed governance states | valid persisted state is `requires_authoritative_activation` and `not_authorized_for_candidate_or_employment_decision` |
| Immutable audit/outbox | `audit_event_record_id` + scope trigger | exact subject/purpose/actor/evidence/time/result and `integration_hub` outbox required |
| Effective and system-recorded time | effective range + recorded range | backdated `recorded_from` rejection, bitemporal exclusion, correction-only closure |
| Tenant isolation | FORCE RLS on both relations | `NOSUPERUSER NOBYPASSRLS` reader sees only its tenant; missing context sees no rows |
| Data minimization | relation shape | no candidate/person identifiers, PII, raw rule text, scores, compensation or model output columns |
| History integrity | history and TRUNCATE guards | in-place rewrite, DELETE and TRUNCATE fail closed; anchor cannot close before versions |

## Stack discipline

#104 is the dependency root and must integrate first. This descendant must remain Draft while #104 is unmerged. After #104 integrates, retarget to fresh protected `develop`, refetch exact head/base/rules/reviews/threads/checks, rerun all applicable hosted evidence on the resulting exact head, and do not transfer predecessor checks or reviews.
