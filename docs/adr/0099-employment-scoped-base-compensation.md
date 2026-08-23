# ADR 0099: Employment-scoped bitemporal base compensation

- Status: Active PR
- Decision date: 2026-08-23
- Protected-main baseline: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`

## Context

Protected main stores `compensation_record` against `person_record`. That shape cannot distinguish compensation belonging to concurrent employments for the same Person and records an amount without a pay-rate period, so the amount is not independently interpretable as hourly, monthly, annual, or another supported period. Because compensation is an Employment term rather than a Person identity attribute, continuing to create person-scoped rows would preserve ambiguity in a high-sensitivity HR fact.

## Decision

Introduce `employment_base_compensation_record` as one durable tenant-qualified base-compensation anchor per `employment_record`, with mutable business truth in `employment_base_compensation_version`.

Each new compensation identity must satisfy the canonical Orgmetra operational-UUID contract, so RFC 9562 Nil and Max sentinels cannot become durable anchor or version identities. Each version stores:

- `base_compensation_amount` as fixed-scale `numeric(19,4)` and rejects negative values and PostgreSQL `NaN`;
- `currency_code` as a three-letter uppercase transport code;
- `pay_rate_period_code` from the controlled vocabulary `hour`, `day`, `week`, `biweekly`, `semimonthly`, `month`, or `year`;
- independent half-open effective and system-recorded intervals.

A GiST exclusion constraint prevents two versions for the same compensation anchor from being simultaneously valid in both effective and system-recorded time. Existing bitemporal history guards permit only closure of an open recorded interval rather than in-place rewriting. Statement-level `BEFORE TRUNCATE` guards plus privilege revocation prevent table-wide erasure from bypassing those row-level correction rules. Tenant-qualified foreign keys bind compensation to the correct Employment, and forced row-level security applies independently to both new relations.

System-recorded time has two explicit enforcement modes. Both the compensation anchor and version default `recorded_from` to PostgreSQL `transaction_timestamp()` and a BEFORE INSERT trigger rejects a supplied value that differs from the current transaction timestamp; INSERT also requires `recorded_to IS NULL`. On closure, a BEFORE UPDATE guard does not assign `recorded_to` itself: it accepts a changed `recorded_to` only when the supplied database value equals the same PostgreSQL transaction timestamp, after which the generic history guard permits closure of the open interval. PostgreSQL defines `transaction_timestamp()` as the transaction start time and keeps it stable within one transaction, giving all compensation facts created or closed by one transaction one consistent system-knowledge coordinate. Business-effective dates remain independently caller-supplied governed facts.

The legacy person-scoped `compensation_record` remains readable for historical compatibility but rejects new inserts. Existing rows are not automatically converted because protected main does not contain enough information to infer the Employment or pay-rate period without fabricating provenance. A later governed migration may map a legacy row only when authoritative source evidence supplies those missing facts.

## Currency boundary

ISO 4217:2015 specifies the structure of three-letter alphabetic currency codes. This slice validates that transport shape only; it does not claim that every syntactically valid three-letter value is a currently assigned ISO currency. Currency-catalog membership belongs in a separately versioned authoritative reference-data boundary rather than being frozen into a database CHECK constraint.

## Consequences

Concurrent employments can carry independent base-compensation truth without conflating one Person's employment terms. Historical corrections remain reconstructable across business time and system-recorded time, while a client cannot backdate the system-knowledge start, pre-close a new fact, choose an arbitrary closure instant, persist reserved UUID sentinels, encode `NaN` as compensation, or erase the relations with `TRUNCATE`. The model is deliberately limited to base compensation: bonus, equity, allowance, payroll calculation, taxation, and total-rewards valuation are not implied by these relations.

PR #48 remains the separate human review/evidence boundary for proposed compensation changes; this ADR does not duplicate that packet or grant mutation authority.

## Verification

`tests/test_employment_compensation_core_postgres.sh` proves concurrent-employment separation, tenant-qualified references, legacy-write rejection, system-recorded start/closure semantics, controlled amount/currency/rate-period shape, bitemporal non-overlap, correction-not-rewrite, and forced-RLS visibility. `tests/test_employment_compensation_review_regressions_postgres.sh` independently proves reserved UUID sentinel rejection, `NaN` rejection, and table-wide TRUNCATE protection. `.github/workflows/employment-compensation-core-quality.yml` runs both contracts against the exact pull-request head and verifies this ADR remains registered in the canonical ADR index.