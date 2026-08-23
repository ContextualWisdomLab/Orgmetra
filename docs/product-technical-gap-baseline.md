# Product and technical gap baseline

Inventory date: 2026-08-23 (Asia/Seoul). Protected `develop` head observed: `9e3e4847510e1e612b48474ba42b177b8ed824df`.

This document is a point-in-time buyer/product planning snapshot. It is **not** merge authorization, branch-protection truth, or a substitute for fresh GitHub state. Every execution loop must refetch all open PRs/issues, exact heads and bases, stacks, reviews/threads, applicable exact-head workflows, and effective repository rules before acting.

Orgmetra owns authoritative HRIS employment truth inside its published boundaries. Keyverse remains the read-only identity owner through its published OIDC/SCIM contracts. For the currently published People mutation API, the tenant header is `X-Tenant-Reference`; the ASGI implementation normalizes HTTP header names to lower case before parsing it and binds it to the authoritative tenant UUID. Orgmetra does not invent or issue a foreign identity-provider subject.

Finance/accounting journal ownership and commercial billing/collection ownership are **not accepted Orgmetra architecture in this snapshot**. Treat those integrations as planned/out-of-scope until an owner contract is published and accepted into Orgmetra's canonical architecture/traceability. Psychometrics Commons and other dedicated-writer CWL repositories remain read-only dependencies consumed only through their published contracts.

Next operator action: do not self-approve. Process the live open-PR graph oldest/dependency-root first. Merge only an unchanged exact head after every applicable current-head gate is terminal GREEN, required conversations are resolved, qualifying independent non-author approval is present, and `develop` has actually enforceable protection. Short-lived model/status checks are not substitutes for those gates unless the live repository policy explicitly makes them qualifying evidence.

## Merged buyer-visible anchors on protected develop

This table is a selected set of shipped anchors relevant to the current buyer-gap analysis, not a replacement for Git history.

| Merged PR | Capability |
|---|---|
| #26 | `validity_study_case_record` integrity (migration 0010) |
| #28 | Performance-criterion Job-scope guard (migration 0011) |
| #31 | Governed People mutation API |
| #38 | Governed Job Analysis snapshot persist/read |
| #41 | Governed candidate evidence intake |
| #43 | Governed offer approval packet |

Do not revive those merged heads. Extend protected truth through a new owner-scoped change only when a fresh buyer gap still exists.

## Open-PR snapshot

The entries below are useful anchors only. They are intentionally not an authoritative or exhaustive queue; live execution order comes from a fresh GitHub graph and remains oldest/dependency-root first.

### Draft / dependency-constrained examples

| PR | Head SHA | Branch | Current snapshot reason |
|---|---|---|---|
| [#99](https://github.com/ContextualWisdomLab/Orgmetra/pull/99) | `09dc3135606669cdd60778db531cd3f6af34e171` | `feat/employment-compensation-core` | Draft in fresh GitHub state; do not infer readiness from its body |
| [#82](https://github.com/ContextualWisdomLab/Orgmetra/pull/82) | `0c3a776f2e2c6f93c25e11c5c3ce3fa66a10b5c9` | `feat/outbox-retry-policy` | Stacked on #51; dependency-first |
| [#77](https://github.com/ContextualWisdomLab/Orgmetra/pull/77) | `9b02cb911377a5beb9f541e9acf2eb51ff065ee9` | `feat/hr-data-disposition-request` | Stacked on #76; dependency-first |
| [#67](https://github.com/ContextualWisdomLab/Orgmetra/pull/67) | `cf59b3001fa58e5a978099c2a5692a03f4849fdd` | `feat/candidate-withdrawal-governance` | Stacked on #66; dependency-first |
| [#58](https://github.com/ContextualWisdomLab/Orgmetra/pull/58) | `c79a6ed49627e6a47947f171aeeed2bf02a8c152` | `build/validation-analysis-reproducibility` | Stacked on #57; dependency-first |

Keep a PR Draft whenever any applicable exact-current-head required workflow is absent, queued, pending, cancelled, skipped-required, neutral, failed, or stale; when a valid defect remains unresolved; or when its stack dependency has not integrated. Do not transfer predecessor checks or reviews.

### Ready-for-review examples on develop

These are snapshot examples only; re-fetch each head, base, review state, threads, workflows, and effective repository rules before acting.

| PR | Head SHA | Capability |
|---|---|---|
| [#40](https://github.com/ContextualWisdomLab/Orgmetra/pull/40) | `8d8896b14db10a5a4981f0b9e209ea00ee3be64c` | Governed structured interview plan |
| [#42](https://github.com/ContextualWisdomLab/Orgmetra/pull/42) | `9b871a3245671f0d14ea56e103ac0d9b91482d43` | Selection outcome monitoring plan |
| [#44](https://github.com/ContextualWisdomLab/Orgmetra/pull/44) | `482d2970cf872cb6f0b4e15fb8805f8bbfd990ff` | Performance review packet |
| [#45](https://github.com/ContextualWisdomLab/Orgmetra/pull/45) | `e0af2501d540de48f7c0e0e3d09ac3e2e5417d2b` | Assignment change review packet |
| [#46](https://github.com/ContextualWisdomLab/Orgmetra/pull/46) | `595c190e30e499abea1284c7307ea0783ada1efd` | Employment separation review packet |
| [#80](https://github.com/ContextualWisdomLab/Orgmetra/pull/80) | `2300c0a0605d89e58aa70ac04b0dee9a7d516882` | Candidate offer response evidence |
| [#81](https://github.com/ContextualWisdomLab/Orgmetra/pull/81) | `78a9cb1e047db5c79ca855b992d44749b9214992` | Contextual Orchestrator draft evidence |
| [#94](https://github.com/ContextualWisdomLab/Orgmetra/pull/94) | `3f67182bb3065f2fc8fd974bfdd75a390d8a8fdc` | Bitemporal Position reporting hierarchy |
| [#95](https://github.com/ContextualWisdomLab/Orgmetra/pull/95) | `adf055d79d188ba18d06ecf80dc1117858c987f4` | Position reporting-change review |
| [#96](https://github.com/ContextualWisdomLab/Orgmetra/pull/96) | `b9f8e3d291c4bdcd2f0aa5f9d0378dea09e5e7cd` | Organization hierarchy-change review |
| [#97](https://github.com/ContextualWisdomLab/Orgmetra/pull/97) | `9715b06d0a459aed7f29293e02de8c2a452e2b87` | Bitemporal Position vacancy evidence |
| [#98](https://github.com/ContextualWisdomLab/Orgmetra/pull/98) | `9aeeb204acce429f85b028029c9531a5b05f37e1` | Governed HR document evidence |

Many other open roots exist. Never use this table to skip an older root or an independently actionable lane.

## Buyer-facing gaps after the open queue

Do not open withholding, payroll-pay, statutory accounting, or year-end settlement tables/UI inside Orgmetra without an accepted owner boundary.

1. Job-grade design against a persisted Job Analysis snapshot, with a normalized grade/band model and accessible Storybooked interaction.
2. Job-analysis LLM draft assistance through Contextual Orchestrator/NVIDIA NIM, with semantic-unit provenance and mandatory human confirmation before snapshot persistence.
3. Offer-to-hire close: connect governed candidate offer response to the authoritative confirmed-hire mutation path without turning response evidence into hire authority.
4. Vacancy-to-assignment: let an authorized operator fill/freeze a staffable Position through authoritative Assignment truth, preserving bitemporal and audit/outbox evidence.
5. Purpose-bound document retrieve/export for governed HR document evidence with field minimization, retention/export controls, and immutable audit rather than indiscriminate masking.
6. For new buyer-visible screens, maintain Storybook, design tokens, accessibility evidence, wireframes, and a governed Figma/Product Design handoff when material.
7. External finance/accounting or billing integration remains planned until a published owner API/event contract is accepted; Orgmetra must not create statutory-account truth or direct cross-service application-table SQL.

## Technical non-negotiables

- Exact 100% owned production statement/branch coverage where tooling exposes it, plus beginner-readable public docs/docstrings and realistic round-trip/security/privacy/concurrency/recovery cases.
- Database objects use descriptive two-or-more-word `snake_case`, 3NF by default, tenant/context isolation, opaque public IDs, and distinct business/effective versus system-recorded time.
- Job, Position, and Assignment remain separate authoritative concepts.
- Necessary PII stays usable only through purpose-bound authorization, least privilege, field minimization, encryption, retention/export controls, and immutable audit evidence.
- High-impact employment decisions require explicit accountable human confirmation with actor/purpose/reason/evidence versioning; LLM output remains untrusted draft evidence only.
- Design write paths toward CSAP and SOC 2 evidence readiness without claiming certification.
- Preserve modular MSA extraction boundaries; do not introduce direct cross-service application-table SQL.
- Failed checks are repair triggers at the first causal owner boundary. Review wait on one lane never blocks independent Orgmetra work.

## Execution loop

Each run: refetch protected `develop`, all open PRs/issues and exact heads/bases, dependency ancestry, reviews/threads, exact-head workflows and effective rules; process oldest/dependency-root first; repair verified Orgmetra defects test-first when practicable; rerun exact-head evidence; resolve only addressed threads; and merge only with qualifying independent non-author approval plus actually enforceable protection. Refresh this document only as a snapshot after material state changes; never treat its recorded SHAs as current truth.

## Doctoring (APA 7th)

Equal Employment Opportunity Commission. (1978). *Uniform guidelines on employee selection procedures* (29 C.F.R. Part 1607).

Society for Industrial and Organizational Psychology. (2018). *Principles for the validation and use of personnel selection procedures* (5th ed.).

International Organization for Standardization. (2025). *ISO 30414:2025 Human resource management — Requirements and recommendations for human capital reporting and disclosure*. ISO.

American Educational Research Association, American Psychological Association, & National Council on Measurement in Education. (2014). *Standards for educational and psychological testing*.
