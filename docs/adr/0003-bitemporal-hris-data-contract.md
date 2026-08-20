# ADR 0003: Bitemporal HRIS data contract

## Status

Status: Accepted

## Context

HR records change over time, and the system can learn facts after they became effective. A hire date, a manager, a job title, or a seat status may be corrected weeks later. Selection and validity analyses must reconstruct both what was true in the business and what Orgmetra knew at a decision point. Stable entity identity and versioned facts have different temporal responsibilities.

Jensen and Snodgrass (1999) summarize the established temporal-database distinction between valid time (when a fact was true in the world) and transaction time (when the database recorded that fact). Snodgrass (1999) shows how to keep those two timelines as first-class SQL intervals rather than overwriting a current row. Orgmetra uses that published bitemporal model. It does not invent a third time dimension or a product-specific temporal algebra.

Allen (1983) treats interval relations such as overlap, meets, and during as first-class knowledge. Half-open, non-empty intervals make those overlap tests deterministic: an end, when present, is strictly later than the start, and adjacent periods can meet without double-counting the boundary day.

A later correction must not leak into an earlier reconstruction. Jensen and Snodgrass require an explicit knowledge cutoff so a query can ask what was known as of a recorded time. Without that cutoff, a validity study or an audit replay would silently adopt facts the original decision-maker could not have seen.

## Decision

Orgmetra distinguishes:

- **entity anchors**, such as `person_record`, whose immutable identifier is system-versioned and whose mutable attributes are not stored on the anchor; and
- **versioned HRIS facts**, such as `person_name_record`, employment, organization, job, position, assignment, criterion, and compensation records.

Every versioned HRIS fact keeps effective time separate from system-recorded time. Intervals are non-empty and half-open: an end value, when present, must be strictly later than its start. Analytical views apply an explicit knowledge cutoff so facts recorded later cannot leak into an earlier decision reconstruction. Single-valued fact families must also guarantee that one effective-time plus knowledge-time coordinate resolves to at most one version; legitimate multiple-membership facts such as assignments use their relationship-specific allocation rules instead of that exclusion policy.

High-impact decisions and their evidence are immutable event records rather than mutable bitemporal facts. Corrections create a new attributable decision or evidence record; they do not rewrite the prior record.

Operators reconstruct history by naming the tenant, the effective day or interval, and the knowledge cutoff. A correction closes the open recorded interval and inserts a replacement fact. In-place business mutation of a recorded fact is rejected. Adjacent half-open intervals may meet; overlapping single-valued versions are a conflict, not a merge.

## Consequences

- Historical organization, job, manager, assignment, and person-name states remain reconstructable at a stated effective time and knowledge cutoff.
- Late corrections do not destroy what the system previously knew; an auditor can compare the original knowledge with the later correction.
- Stable identity does not duplicate mutable descriptive attributes.
- Decision and evidence history remains append-only, so a validity case can export the exact decision the human confirmed.
- Queries and tests are more complex but auditable. Operators must supply a knowledge cutoff instead of reading an implicit “current” snapshot when reconstructing a past decision.
- This ADR does not replace Jensen and Snodgrass or Allen with a new temporal model. Later assignment, exclusivity, and hierarchy rules compose on top of this contract.

## References

The APA 7th bibliography is maintained in `docs/doctoring/REFERENCES.md`. This ADR uses:

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://doi.org/10.1109/69.755613

Snodgrass, R. T. (1999). *Developing time-oriented database applications in SQL*. Morgan Kaufmann. https://lccn.loc.gov/99014298
