# ADR 0004: Framework-independent domain kernel

## Status

Proposed in active implementation PR.

## Context

Core HRIS invariants must be reusable by standalone services, a modular monorepo, tests, migration workers, and future API adapters without importing a web framework or database driver. These invariants are non-mathematical and do not require the Rust psychometric compute policy.

ADR 0003 requires effective/business time and system-recorded time to remain independently reconstructable. A durable person identity is different from a mutable HR fact: the domain package exposes an identity-only `PersonRecord`, while creation and retirement knowledge time are persistence-owned lifecycle metadata. The authoritative persistence contract must therefore retain `recorded_from` and `recorded_to` for the person anchor even though those columns are not duplicated as mutable attributes on the in-memory identity value. Adapters that load or persist a person anchor must carry that lifecycle metadata in their repository envelope rather than silently dropping it.

## Decision

Implement bitemporal people, employment, position, assignment, and candidate-worker invariants in the independently installable `orgmetra-domain` Python package. Keep persistence, authorization, transport, and external integrations outside the package. Include a PEP 561 marker and exact coverage/docstring gates.

Keep durable identity anchors intentionally small. `PersonRecord` contains only the opaque durable identity; persistence owns the recorded lifecycle of that identity. Mutable person names and other effective-dated facts use explicit version records with `BitemporalPeriod`. `EmploymentRecord` and `PositionRecord` are likewise identity-only; status and dates live on version records (ADR 0006). Repository adapters are responsible for preserving the anchor's system-recorded lifecycle alongside the identity, and repository-contract tests require both lifecycle columns to remain present in the authoritative schema.

## Consequences

- Domain behavior is testable without infrastructure.
- Future services can embed the same invariant layer.
- Database constraints must mirror these rules transactionally.
- Person-anchor creation/retirement history remains reconstructable without turning the durable identity object into a mutable fact record.
- A repository adapter that omits the person anchor's `recorded_from` or `recorded_to` violates this ADR even if an identity-only `PersonRecord` can still be constructed.
- Psychometric and mathematical computation remains Rust-first and is not added to this package.

## Acceptance evidence

- Behavioral RED/GREEN tests for every invariant.
- Repository-contract proof that the person persistence record retains `recorded_from` and `recorded_to` while the domain anchor remains identity-only.
- Exact 100% production statement and branch coverage.
- Python 3.11-3.14 CI.
- Installed-wheel smoke and `py.typed` presence verification before release.
