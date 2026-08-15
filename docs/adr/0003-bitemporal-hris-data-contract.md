# ADR 0003: Bitemporal HRIS data contract

## Status

Accepted baseline.

## Context

HR records change over time, and the system can learn facts after they became effective. Selection and validity analyses must reconstruct both what was true and what was known at a decision point. Stable entity identity and versioned facts have different temporal responsibilities.

## Decision

Orgmetra distinguishes:

- **entity anchors**, such as `person_record`, whose immutable identifier is system-versioned and whose mutable attributes are not stored on the anchor; and
- **versioned HRIS facts**, such as `person_name_record`, employment, organization, job, position, assignment, criterion, and compensation records.

Every versioned HRIS fact keeps effective time separate from system-recorded time. The database rejects reversed effective or recorded intervals. Analytical views apply an explicit knowledge cutoff so facts recorded later cannot leak into an earlier decision reconstruction.

High-impact decisions and their evidence are immutable event records rather than mutable bitemporal facts. Corrections create a new attributable decision or evidence record; they do not rewrite the prior record.

## Consequences

- Historical organization, job, manager, assignment, and person-name states remain reconstructable.
- Late corrections do not destroy what the system previously knew.
- Stable identity does not duplicate mutable descriptive attributes.
- Decision and evidence history remains append-only.
- Queries and tests are more complex but auditable.
