# orgmetra-domain

`orgmetra-domain` is Orgmetra's independently importable domain kernel for non-numerical HRIS invariants.

## Current capabilities

- Half-open, non-empty effective-time and system-recorded-time intervals.
- Durable person anchors separated from effective and system-recorded person-name facts.
- Durable organization and job anchors separated from bitemporal descriptive versions.
- Distinct employment, organization, job, position, and assignment concepts.
- Bitemporal organization hierarchy facts and versioned job definitions, kept distinct from positions that instantiate them.
- Multiple simultaneous assignments with allocation validation.
- Append-only, idempotent candidate-to-worker linkage.
- Explicit domain errors for invalid or conflicting operations.

## Boundaries

This package contains no database client, web framework, authentication provider, LLM, or psychometric arithmetic. Services own persistence and authorization. Psychometric and mathematical production computation remains Rust-first in its owning product.

## Example

```python
from datetime import date, datetime, timezone
from uuid import uuid4

from orgmetra_domain import BitemporalPeriod, PersonNameRecord, PersonRecord

person = PersonRecord(uuid4())
period = BitemporalPeriod(
    effective_from=date(2026, 1, 1),
    effective_to=None,
    recorded_from=datetime.now(timezone.utc),
    recorded_to=None,
)
name = PersonNameRecord(uuid4(), person.person_record_id, "Ada Lovelace", period)
```

The durable `PersonRecord` never stores mutable descriptive attributes. A name correction appends or supersedes a `PersonNameRecord` version while preserving the same person identity and the historical knowledge timeline. `OrganizationUnitRecord` and `JobProfileRecord` follow the same anchor pattern; `OrganizationUnitVersionRecord` and `JobProfileVersionRecord` carry descriptive facts over business and system time. `PositionRecord` therefore references durable organization/job identities rather than one historical description.

## Quality

```bash
python -m pip install --only-binary=:all: --require-hashes -r requirements/ci.txt
./scripts/run_domain_quality.sh
```

The quality command executes behavioral tests, exact 100% owned production statement/branch coverage, public docstring validation, and repository supply-chain contracts.
