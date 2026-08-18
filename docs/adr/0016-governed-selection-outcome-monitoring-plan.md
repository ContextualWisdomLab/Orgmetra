# ADR 0016: Governed selection-outcome monitoring plan

- **Status:** Proposed — active PR only
- **Decision scope:** Selection validity / workforce intelligence governance

## Context

Orgmetra already owns Job-scoped selection and post-hire evidence boundaries, but protected `develop` does not define a buyer-facing contract for planning recurring selection-outcome monitoring without copying candidate-level protected-attribute values or turning a screening heuristic into an automated legal or employment decision.

The EEOC's common interpretation of the Uniform Guidelines directs users to examine the total selection process first for each job, describes the four-fifths rule as a rule of thumb rather than a legal definition, and notes that small samples, statistical significance, practical significance, and other evidence can matter. ISO 30405:2023 also treats reviewing and learning as part of recruitment practice. SIOP's fifth-edition Principles provide the professional validation framework for personnel selection procedures.

## Decision

Orgmetra will expose a transport-neutral `SelectionOutcomeMonitoringPlan` that binds:

- one operational tenant and authoritative Job;
- one total selection-process reference;
- exact aggregate population and selection-outcome snapshot references and SHA-256 digests;
- exact protected-attribute handling, small-sample interpretation, and statistical-analysis plan references and digests;
- an accountable requester and a distinct accountable reviewer;
- an explicit monitoring business-date window and evidence-generation instant.

The contract is aggregate-only and carries no candidate identity, protected-attribute value, individual assessment score, individual employment decision, or free-form model output. It fixes `analysis_scope` to `total_selection_process_by_job`, `decision_authority` to `human_review_only`, and state to `requires_human_review`. It does not calculate selection rates, mechanically apply the four-fifths heuristic, test statistical significance, infer discrimination, or authorize a process change.

Any later analytics or persistence boundary must independently enforce purpose-bound authorization, minimum-necessary protected-attribute access, small-sample controls, provenance, immutable audit evidence, and accountable human interpretation. Results are evidence for review, not an automated high-impact employment decision or certification/legal conclusion.

## Consequences

- Buyers obtain a deterministic governance envelope for recurring selection monitoring without creating a second psychometrics/statistics engine inside Orgmetra.
- The total-process-by-Job scope is explicit before any future component drill-down.
- Privacy risk is reduced because individual protected-attribute values and candidate records remain outside the plan envelope.
- The four-fifths rule cannot be represented as an automatic pass/fail legal rule by this contract; interpretation remains with authorized analysts and accountable humans.
- Psychometric/statistical production compute remains owned by the appropriate Psychometrics Commons / fast-mlsirm / TEPP contract when those kernels are needed.

## References

See `docs/doctoring/selection-outcome-monitoring-references.md`.
