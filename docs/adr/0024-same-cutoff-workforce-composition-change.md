# ADR-0024: Workforce composition change uses one recorded-time cutoff

**Status:** Proposed on active PR
**Decision owner:** Orgmetra

## Context

Protected Orgmetra can reconstruct a `WorkforceCompositionSnapshot` for one tenant at an effective business date and an explicit recorded-time knowledge cutoff. Buyers also need to compare workforce composition across two effective dates. A naive comparison can be misleading if the opening snapshot is reconstructed with an earlier knowledge cutoff than the closing snapshot: later corrections then appear indistinguishable from actual business-time workforce movement.

ISO 30414:2025 is the current published second edition of the human-capital reporting and disclosure standard. Its public catalogue lists workforce composition, mobility and succession planning, and workforce turnover among core reporting areas. This ADR uses that public scope only; it does not reproduce licensed metric definitions or claim ISO certification.

## Decision

Orgmetra adds a pure `WorkforceCompositionChangeSnapshot` and builder in the HRIS kernel.

- Both endpoint snapshots must belong to the same authoritative tenant.
- The opening effective date must be strictly earlier than the closing effective date.
- Both endpoint snapshots must use one exact `known_at` recorded-time cutoff. Effective-time change is therefore compared while knowledge time is held constant.
- The builder resolves that cutoff once to a detached UTC datetime before constructing either endpoint; caller-owned timezone providers cannot cause the two endpoint reconstructions to observe different recorded times.
- Each endpoint is built through the existing workforce-composition function, so contradictory bitemporal facts, invalid assignment coverage, impossible employment concurrency, over-allocation, and overfilled Position capacity continue to fail closed before aggregation.
- The comparison exposes net changes in distinct-person headcount, reportable employment count, staffed assignment count, staffed FTE, unassigned-person count, and deterministic per-status counts.
- The contract deliberately does **not** label a net change as a hire, separation, transfer, turnover event, cause, forecast, protected-attribute effect, or recommendation. Those claims require event-specific governed evidence that this aggregate comparison does not possess.
- Canonical JSON embeds only the two aggregate endpoint snapshots, their SHA-256 digests, aggregate deltas, the opaque tenant identifier, and schema version. It does not serialize row-level Person, Employment, Assignment, or Position identifiers.
- The result is descriptive workforce-intelligence evidence only and cannot authorize a high-impact employment action.

## Consequences

Buyers can compare two business dates without silently mixing later-recorded corrections into the change metric. The comparison is deterministic and audit-correlatable while remaining aggregate-only. Because it is intentionally not a turnover calculator, a later turnover/mobility slice must bind authoritative employment-transition evidence and its denominator/period policy explicitly rather than deriving causal labels from endpoint subtraction.

The slice adds no persistence table, dashboard, export endpoint, forecasting model, diversity inference, or automated decision authority. Authorization and presentation remain at their owning boundaries.

## Verification

`packages/hris-kernel/tests/test_workforce_composition_change.py` covers realistic effective-date change, exact Decimal FTE deltas, deterministic source-order independence, aggregate-only canonical evidence, same-tenant enforcement, strictly forward effective dates, and one shared knowledge cutoff. `.github/workflows/workforce-intelligence-quality.yml` runs the complete HRIS kernel at exact 100% owned production statement and branch coverage.

## References

APA 7 references and current public standard metadata are recorded in `docs/doctoring/workforce-composition-change-references.md`.
