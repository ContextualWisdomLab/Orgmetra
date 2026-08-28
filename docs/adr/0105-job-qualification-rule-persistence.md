# ADR 0105: Governed Job qualification-rule persistence

Status: Active PR

## Context

Protected `develop` stores Job Analysis Task/FJA/KSAO evidence, and PR #104 adds a human-reviewed qualification-rule proposal that is explicitly non-authorizing. Orgmetra still needs a durable, tenant-isolated persistence boundary so a reviewed rule artifact can be versioned without collapsing Job, Job Analysis, candidate evaluation and employment-decision authority into one record.

OPM describes job analysis as the foundation for assessment and selection decisions and says qualification standards should be supplemented by job analysis rather than used as a substitute for applicant KSA/competency analysis. This is design evidence, not a claim that Orgmetra implements U.S. federal qualification policy.

## Decision

Introduce two normalized relations in migration `0019_job_qualification_rule_persistence.sql`:

- `job_qualification_rule_record` is the durable tenant-qualified anchor owned by one authoritative Job.
- `job_qualification_rule_version` is the bitemporal reviewed version. It references one Job Analysis snapshot, controlled rule category, SHA-256 artifact/Task/KSAO/source/review provenance, reviewer, evidence version, effective time, system-recorded time and one immutable audit event.

Before INSERT, the database re-resolves that the anchor is open, the Job Analysis snapshot belongs to the same Job, the snapshot is human-reviewed and `analysis_validated`, and its content digest exactly matches the supplied snapshot digest. The audit event must be same-tenant, have the exact reviewed rule subject/purpose/actor/evidence/time/result, and have an `integration_hub` outbox record.

The version always persists with `activation_state = requires_authoritative_activation` and `decision_authority_state = not_authorized_for_candidate_or_employment_decision`. Persisting reviewed evidence therefore does not authorize candidate screening, rejection, ranking, hiring or any other high-impact employment action. A later activation/use boundary must re-resolve current authority and emit its own immutable evidence.

Raw qualification-rule text, candidate/person identifiers, PII, assessment outcomes, cut scores, compensation and model output are intentionally absent from these relations. The artifact is represented by digest and controlled metadata only.

System-recorded `recorded_from` must equal PostgreSQL `transaction_timestamp()`; callers cannot backdate recorded truth. Effective time remains independent business time. Recorded history is append/correction-only, TRUNCATE is rejected, and FORCE RLS uses the existing transaction-local tenant context. Every new trigger function pins `search_path` to `pg_catalog, public, pg_temp`, while migration-time object creation uses the trusted `public, pg_catalog` path. A durable anchor cannot close while a child version remains recorded open.

## Consequences

- Job qualification evidence becomes queryable and historically reconstructable without becoming autonomous decision logic.
- Job/Job Analysis drift, foreign-tenant evidence, unvalidated analysis, digest mismatch, missing audit/outbox evidence and post hoc history rewrites fail closed.
- The database stores only governance metadata and evidence digests; customer-facing rule content remains in its separately governed artifact boundary.
- PR #104 remains the dependency root. This persistence PR stays Draft until #104 integrates, then must be retargeted and revalidated against fresh protected `develop` without inheriting predecessor evidence.
- This ADR does not claim legal compliance, validity, certification, or production activation of qualification rules.

## Primary sources reviewed

See `docs/doctoring/job-qualification-rule-persistence-references.md`.
