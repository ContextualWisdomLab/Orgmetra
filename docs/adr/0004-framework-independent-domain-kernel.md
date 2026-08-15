# ADR 0004: Framework-independent domain kernel

## Status

Proposed in active implementation PR.

## Context

Core HRIS invariants must be reusable by standalone services, a modular monorepo, tests, migration workers, and future API adapters without importing a web framework or database driver. These invariants are non-mathematical and do not require the Rust psychometric compute policy.

## Decision

Implement bitemporal people, employment, position, assignment, and candidate-worker invariants in the independently installable `orgmetra-domain` Python package. Keep persistence, authorization, transport, and external integrations outside the package. Include a PEP 561 marker and exact coverage/docstring gates.

## Consequences

- Domain behavior is testable without infrastructure.
- Future services can embed the same invariant layer.
- Database constraints must mirror these rules transactionally.
- Psychometric and mathematical computation remains Rust-first and is not added to this package.

## Acceptance evidence

- Behavioral RED/GREEN tests for every invariant.
- Exact 100% production statement and branch coverage.
- Python 3.11-3.14 CI.
- Installed-wheel smoke and `py.typed` presence verification before release.
