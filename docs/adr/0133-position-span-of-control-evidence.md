# ADR 0133: Position span-of-control evidence is structural, bitemporal, and non-authorizing

- Status: Proposed
- Scope: active PR #133 only; not protected-`develop` truth until integrated
- Parent owner: PR #94 Position-to-Position solid-line reporting hierarchy

## Context

Orgmetra can reconstruct a tenant-scoped solid-line Position reporting graph on PR #94, but buyers still need a defensible organization-design metric answering a narrower question: how many direct-report **Position seats** are attached to each manager Position at one business date and one system-knowledge cutoff?

Span of control is empirically consequential, but research does not support treating one universal number as optimal across all organizations or levels. Work complexity, functional diversity, hierarchy level and organizational goals change the relationship. Encoding a universal target would turn descriptive structure into an unsupported management or employment recommendation.

## Decision

Orgmetra will expose `PositionSpanOfControlSnapshot` as PII-minimized structural workforce evidence derived only from one exact governed `PositionReportingSnapshot`.

The boundary:

1. counts direct-report Position seats, never workers;
2. preserves the parent's explicit `tenant_record_id`, business `effective_on`, and UTC system `known_at` coordinate;
3. revalidates the parent runtime type, opaque identities, immutable edge shape, unique visible relationship identities, one manager per subordinate, self-edge rejection, and cycle rejection so direct dataclass construction cannot forge downstream evidence;
4. emits manager Position UUID plus positive direct-report Position count in deterministic UUID order;
5. binds canonical JSON with SHA-256 for audit correlation while excluding Person, Employment and Assignment identifiers;
6. labels the result `structural_workforce_evidence` and `not_authorized_for_employment_decision`; and
7. does **not** encode an ideal span, performance score, staffing recommendation, promotion signal, termination signal, or compensation implication.

## Consequences

This slice makes span-of-control structure inspectable without claiming that a wide or narrow span is good or bad. Any future recommendation layer must supply separately governed contextual evidence and human review rather than converting this descriptive count into a high-impact rule.

Persistence, authorized presentation, organization-design simulation and workflow-specific UI remain separate boundaries. PR #94 must integrate first; this child is not shipped truth and cannot inherit parent checks or reviews.

## References

Bell, G. D. (1967). Determinants of span of control. *American Journal of Sociology, 73*(1), 90–101. https://doi.org/10.1086/224439

Meier, K. J., & Bohte, J. (2000). Ode to Luther Gulick: Span of control and organizational performance. *Administration & Society, 32*(2), 115–137. https://doi.org/10.1177/00953990022019371

Theobald, N. A., & Nicholson-Crotty, S. (2005). The many faces of span of control: Organizational structure across multiple goals. *Administration & Society, 36*(6), 648–660. https://doi.org/10.1177/0095399704270585
