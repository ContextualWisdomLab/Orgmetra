# ADR 0002: Federated CWL integration boundaries

## Status

Accepted baseline.

## Context

CWL already has specialist products for identity, communication, psychometrics, temporal analysis, semantic catalogs, document viewing, data migration, retrieval fusion, authoring, and diagrams. Copying them into Orgmetra would create a monolith and duplicate ownership.

## Decision

Orgmetra integrates CWL products through explicit package, API, event, or adapter boundaries. No direct cross-service application-table SQL is allowed.

## Consequences

- Services remain independently deployable.
- Orgmetra keeps employment truth centralized.
- Adapter failures are isolated and visible.
- Contracts must be versioned and tested.
