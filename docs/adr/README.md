# ADR Index

`Status` is the canonical ADR decision state validated against each ADR file. `Provenance` records where that state is evidenced and must not be folded into the status cell, because doing so would bypass the index-to-file status check. `develop` entries below are integrated repository truth, but enforceable branch protection is currently tracked separately by issue #89 and therefore is not claimed here.

| ADR | Title | Provenance | Status |
|---|---|---|---|
| [0001](0001-orgmetra-authoritative-hris-record.md) | Orgmetra owns authoritative HRIS records | — | Accepted |
| [0002](0002-federated-cwl-integration-boundaries.md) | Federated CWL integration boundaries | — | Accepted |
| [0003](0003-bitemporal-hris-data-contract.md) | Bitemporal HRIS data contract | — | Accepted |
| [0004](0004-employment-position-version-and-assignment-binding.md) | Employment and position versions bind assignments | — | Accepted |
| [0005](0005-exclusive-employment-and-staffable-seats.md) | Exclusive employment and staffable seats | — | Accepted |
| [0006](0006-governed-audit-outbox-envelope.md) | Governed audit/outbox envelope and durable persistence | `develop`; protection gap #89 | Accepted |
| [0007](0007-governed-job-analysis-evidence.md) | Governed job-analysis evidence snapshots | `develop`; protection gap #89 | Accepted |
| [0008](0008-purpose-bound-pii-authorization.md) | Purpose-bound PII authorization | `develop`; protection gap #89 | Accepted |
| [0009](0009-performance-criterion-observation-scope.md) | Performance criterion observations require worker-job scope | `develop`; protection gap #89 | Accepted |
| [0010](0010-naruon-calendar-intent-boundary.md) | Naruon calendar intent boundary | `develop`; protection gap #89 | Accepted |
| [0011](0011-bitemporal-workforce-composition.md) | Bitemporal workforce composition | `develop`; protection gap #89 | Accepted |
| [0012](0012-governed-migration-handoff.md) | Governed migration handoff | `develop`; protection gap #89 | Accepted |
| [0013](0013-governed-requisition-review-packet.md) | Governed requisition review packet | `develop`; protection gap #89 | Accepted |
| [0014](0014-job-analysis-snapshot-persistence.md) | Persist governed job-analysis snapshots | `develop`; protection gap #89 | Accepted |
| [0017](0017-governed-offer-approval.md) | Governed offer approval evidence | `develop`; protection gap #89 | Accepted |
| [0025](0025-governed-candidate-evidence-intake.md) | Govern candidate evidence intake as reference-only evidence | `develop`; protection gap #89 | Accepted |
| [0026](0026-product-technical-gap-baseline.md) | Product and technical gap baseline | active PR #53 | Accepted |
