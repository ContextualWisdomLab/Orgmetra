# ADR 0093: Governed performance-context evidence

## Status

Proposed on active PR #93. Not protected-`develop` truth until independently reviewed and merged. This ADR does not claim a released feature or statistical adjustment method.

## Context

Orgmetra already models performance cycles and criterion observations, but a criterion can be influenced by the work setting in which it was observed. Protected `develop` did not provide a governed boundary that preserves opportunity-to-perform and organizational context provenance without copying raw HR values or granting an automated rating adjustment.

The SIOP *Principles for the Validation and Use of Personnel Selection Procedures* require validation evidence and criterion interpretation to be grounded in the work and the inferences being made. SIOP's 2023 AI-assessment guidance additionally calls out variation in work and irrelevant sources of variance as considerations when identifying outcomes for validation. Field research has also reported associations between situational constraints and both subjective and objective performance criteria. These sources justify retaining reviewed context provenance; they do **not** justify causal adjustment of an individual's rating from this packet alone.

## Decision

Add an Orgmetra-owned `PerformanceContextEvidencePacket` with the following boundaries:

1. **Value minimization.** Store identifiers and cryptographic provenance only. Do not store performance ratings, manager identity, raw constraint measures, compensation, or free-form HR text.
2. **Business and system time.** Represent the reviewed exposure window as a nonempty half-open pair of exact built-in `date` values and record packet issuance with an exact timezone-aware `datetime` canonicalized to UTC.
3. **Multiple-membership evidence.** Preserve bounded, sorted, unique Assignment and Organization reference tuples plus a digest of reviewed membership weights. Downstream analysis must re-resolve authoritative membership and weights; the packet is not an analytical kernel.
4. **Context provenance.** Bind separate SHA-256 digests for opportunity-to-perform, broader work context, manager context, and membership weights so reviewers can distinguish evidence sources without persisting the raw snapshots in the packet.
5. **Human accountability.** Require distinct requester and reviewer references and fixed purpose/reason codes.
6. **No decision authority.** Fix the state to `context_covariate_evidence_only`, `requires_human_review`, `not_authorized_for_performance_rating`, and `not_authorized_for_employment_decision`.
7. **Runtime integrity.** Reject caller-defined primitive/collection subclasses before reviewed operations, use deterministic canonical JSON, keep the packet runtime final, and detect post-issuance mutation plus conflicting live reference reuse through a process-local weak registry.
8. **Service ownership.** No direct cross-service table SQL and no write to any dedicated-writer dependency repository. Statistical estimation remains the responsibility of the relevant governed validation/psychometric boundary.

## Consequences

### Positive

- Validation and workforce analysis can distinguish context provenance from individual criterion evidence.
- Multiple-assignment and organizational membership can be reconstructed without embedding raw contextual HR values.
- Buyers receive an auditable next action rather than an opaque "context adjusted" score.
- The boundary is modular and can later be extracted behind an API/event contract without changing ownership of the HRIS source of truth.

### Costs and limits

- The packet does not establish that a contextual factor caused a performance outcome.
- Digests require authoritative source snapshots to remain retrievable under retention and authorization policy.
- The process-local issuance registry is defense-in-depth only; distributed uniqueness and immutable evidence belong in authoritative persistence/audit transactions.
- Later multilevel, cross-classified, multiple-membership, or temporal estimation must retain true-parameter recovery, bias/MAE/RMSE, interval coverage, and convergence evidence at the numerical-kernel boundary; this ADR does not implement those kernels.

## Verification

`Performance Context Evidence Quality` builds and hash-binds the exact wheel, runs tests outside the source tree under CPython 3.14.7, and requires exact 100% owned production statement and branch coverage plus a clean checkout. Foundation, SAST, Security, and Recovery gates remain independently required before readiness.
