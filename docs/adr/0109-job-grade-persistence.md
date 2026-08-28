# ADR 0109: Persist Job grade assignment truth as bitemporal Job-scoped evidence

Status: Proposed

## Context

Protected `develop` has authoritative Job and persisted Job Analysis truth. PR #101 adds a human-reviewed enterprise-local Job grade/band design packet but deliberately does not persist an authoritative Job-grade fact. Commercial HRIS buyers need historically reconstructable Job architecture without conflating grade with Person, Position, Assignment, compensation, or an employment decision.

## Decision

When PR #101 is available, Orgmetra will persist Job-grade truth through three normalized owner relations:

- `job_grade_definition_record`: immutable enterprise-local grade/band definition evidence identified by grade code, band code, and exact reviewed definition SHA-256;
- `job_grade_assignment_record`: one stable tenant-qualified assignment anchor per authoritative Job;
- `job_grade_assignment_version`: bitemporal effective/system-recorded assignment of one Job to one immutable grade definition, one validated Job Analysis snapshot, exact reviewed method/provenance, and immutable audit/outbox evidence.

The version boundary stores the exact value-minimized canonical `JobGradeDesignReviewPacket` JSON and SHA-256 rather than accepting an unbound digest. Before insert, PostgreSQL re-resolves the open Job anchor, immutable grade definition, same-Job `analysis_validated` Job Analysis snapshot, exact snapshot digest, packet key/value semantics, reviewer/purpose/reason/chronology, immutable audit event, and `integration_hub` outbox correlation.

System-recorded time is PostgreSQL transaction time. Business/effective time remains independent. History is correction-not-rewrite, owned relations use FORCE RLS with tenant context, and the migration plus trigger functions pin trusted `search_path` values. A grade assignment is authoritative Job-architecture truth only; it remains `not_authorized_for_compensation_or_employment_decision`.

## Consequences

Grade/band semantics remain enterprise-local and versioned by immutable definition evidence rather than a universal taxonomy. A semantic definition change creates a new definition record; a Job's effective grade change creates a new bitemporal assignment version. Person, Position, Assignment, compensation, assessment output, candidate data, and free-form HR text remain outside these relations.

This active PR is stacked on #101. It is not protected-main truth and cannot be review-ready or merge-ready until #101 integrates, the descendant is retargeted to fresh `develop`, and every applicable current-head gate is rerun without predecessor evidence.

## Primary evidence

PostgreSQL 16 row-level-security policy semantics and exclusion constraints are used for tenant isolation and bitemporal overlap prevention. OPM Factor Evaluation System material is methodological evidence that factor-based evaluation can support auditable grade determination; Orgmetra does not adopt U.S. federal grade rules as its enterprise taxonomy.
