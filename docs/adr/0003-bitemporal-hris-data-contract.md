# ADR 0003: Bitemporal HRIS data contract

## Status

Accepted baseline.

## Context

HR records change over time, and the system can learn facts after they became effective. Selection and validity analyses must reconstruct both what was true and what was known at a decision point.

## Decision

Orgmetra stores effective time and system-recorded time separately for HRIS facts. Analytical views must use the appropriate cutoff to prevent future-information leakage.

## Consequences

- Historical organization, job, manager, and assignment states remain reconstructable.
- Late corrections do not destroy what the system previously knew.
- Queries and tests are more complex but auditable.
