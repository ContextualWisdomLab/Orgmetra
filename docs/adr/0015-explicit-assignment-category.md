# ADR 0015: Explicit assignment category is authoritative HRIS truth

- Status: Proposed
- Date: 2026-09-02
- Owners: `people_core` and the Organization–Job–Position–Assignment domain boundary

## Context

An `assignment_record` already states that one person, through one employment, occupies one position for an effective/system-time interval and allocation ratio. Allocation does not answer a different business question: which assignment is the worker's primary reporting/work relationship and which concurrent assignment is secondary or temporary-factor-team work. Inferring that decision from the largest allocation, row order, position identity, or graph topology would turn storage coincidence into HR truth and would make downstream authorization and context-graph consumers disagree after corrections.

The ecosystem contract in `ContextualWisdomLab/context-graph-contracts#23` needs a non-heuristic source for primary-versus-secondary organization membership. Orgmetra owns that source because it owns employment and assignment facts; consumers may translate the published value through an anti-corruption layer but must not author or infer it.

Bitemporal interpretation matters because the same assignment can be corrected later and because two assignments may overlap in effective time while being known at different system times. Allen (1983) and Jensen and Snodgrass (1999) provide the temporal-data basis for treating interval overlap and recorded-time knowledge as first-class semantics rather than collapsing them into a current-row flag. ISO 30400:2022 is used only as HR vocabulary context, not as evidence that ISO prescribes these exact category codes.

## Decision

`assignment_record.assignment_category_code` is an authoritative value object with two values for every new write:

- `primary`: the one primary assignment permitted for an employment at a bitemporal coordinate;
- `concurrent_secondary`: an additional concurrently valid assignment.

Migration provenance may contain `legacy_unspecified` only for rows created before this contract. Application commands and new direct database writes cannot create that sentinel, and no application or migration may convert it by heuristic inference.

The Assignment aggregate remains rooted in the stable `assignment_record_id` and is evaluated within tenant plus `employment_record_id`. Its invariants are:

1. category is explicit on every new mutation;
2. at most one `primary` assignment is visible for the same tenant and employment at overlapping effective and recorded intervals;
3. concurrent secondary assignments remain subject to the existing assignment-portfolio allocation ceiling and employment/position coverage invariants;
4. category participates in the mutation's semantic idempotency digest, so replaying one Idempotency-Key with a different category is a conflict rather than the same command; and
5. historical `legacy_unspecified` remains readable but never gains an inferred primary/secondary meaning.

The `people_core` application service validates the value before authorization/persistence composition, the HRIS domain service validates the visible portfolio, and PostgreSQL independently enforces the forward-write vocabulary plus the single-primary overlap invariant. The HTTP and OpenAPI contracts expose only `primary | concurrent_secondary` for new commands.

## DDD boundary and context map

Ubiquitous language uses **Assignment Category**, **Primary Assignment**, **Concurrent Secondary Assignment**, and **Legacy Unspecified History**. `people_core` is the upstream authoritative bounded context. Keyverse is an identity/authorization peer and does not own assignment category. Context-graph consumers are downstream and receive the classification through versioned contracts/ACL translation. No shared kernel is introduced for the category vocabulary; only the published contract crosses the boundary.

The aggregate/entity/value-object split is:

- aggregate/entity: `assignment_record` identified by `assignment_record_id`;
- value object: `assignment_category_code`;
- domain service: bitemporal assignment-portfolio validation;
- repository boundary: the People mutation port/PostgreSQL adapter;
- domain event/provenance boundary: existing People mutation audit/outbox evidence, whose command digest includes category semantics.

## Persistence and concurrency consequences

Migration 0017 backfills pre-contract rows explicitly as `legacy_unspecified`. Its table CHECK accepts only the three known storage values so historical rows remain valid when their system-time interval is closed. A dedicated write guard rejects introducing `legacy_unspecified` on INSERT and rejects changing an already classified row back to that sentinel; closing the `recorded_to` interval of a pre-contract legacy row therefore preserves history without inventing a classification. Replacement/current rows still require `primary | concurrent_secondary` through the application/API contract and database write guard. A partial GiST exclusion constraint over tenant, employment, effective interval, and recorded interval rejects two simultaneously visible primary rows without serializing unrelated employments. This preserves normalized assignment facts rather than adding a denormalized 'current primary' pointer and keeps the model in 3NF.

The exclusion key starts with tenant and employment scope, so conflict work is localized to the employment portfolio instead of creating an organization-wide hot partition. Read paths continue to reconstruct bitemporal facts; this ADR does not introduce a cross-service read/write shortcut or direct access to another bounded context's database.

## Security, privacy, and decision authority

Assignment category is employment metadata and can affect authorization context, so it remains tenant- and purpose-bound. It does not itself authorize access or make a hiring, promotion, compensation, termination, or other high-impact employment decision. Downstream consumers must combine it with their own authorized policy context and must not expose internal service boundaries in customer-facing copy.

Tests and documentation use synthetic organization/person identifiers. Production PII is neither indiscriminately masked nor copied into category/audit metadata.

## Verification and traceability

The implementation is test-first: domain/idempotency regression preceded production changes; a PostgreSQL regression then preceded the forward-only persistence repair; and an OpenAPI regression preceded publishing the required command field. A later RED regression proved that system-time closure of pre-contract `legacy_unspecified` history must remain legal; the database repair separates the storage vocabulary from the forward-write guard rather than forcing a guessed category. Exact-head validation must cover People API statement/branch coverage, PostgreSQL compatibility/invariants, Foundation manifest/provenance, Recovery, Security/SAST, and required organization review workflows before ordinary protected-branch integration.

## Consequences

Consumers can distinguish primary from secondary membership without guessing. Historical uncertainty remains explicit rather than silently rewritten. A category correction must follow normal bitemporal correction semantics instead of in-place mutation. The added exclusion constraint introduces conflict detection only where two primary intervals overlap for the same tenant-local employment.

## References

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

International Organization for Standardization. (2022). *ISO 30400:2022 Human resource management — Vocabulary*. ISO. https://www.iso.org/standard/78044.html

Jensen, C. S., & Snodgrass, R. T. (1999). Temporal data management. *IEEE Transactions on Knowledge and Data Engineering, 11*(1), 36–44. https://doi.org/10.1109/69.755613
