# Candidate conversion system-recorded-time references

## Design question

Which database clock should define Orgmetra's `recorded_from` knowledge/system time for one atomic candidate-to-worker conversion transaction?

## Primary technical source

PostgreSQL Global Development Group. (2026). *PostgreSQL 16 documentation: 9.9. Date/time functions and operators*. https://www.postgresql.org/docs/16/functions-datetime.html

The PostgreSQL 16 documentation defines `transaction_timestamp()` as the start time of the current transaction and explains that transaction-current time remains stable throughout the transaction so multiple modifications can bear one consistent timestamp. Orgmetra therefore uses transaction time, rather than caller input or `clock_timestamp()`, for the atomic hire conversion's system-recorded coordinate.

## Interpretation for Orgmetra

- `effective_from` remains the business-effective date and can differ from system time.
- `recorded_from` is database-authored knowledge time and must equal the current PostgreSQL transaction timestamp on INSERT.
- A later correction creates/opens a new system-time fact through the existing governed bitemporal path rather than backdating when Orgmetra learned the fact.
- This choice is an implementation/evidence-integrity contract, not a certification or legal-compliance claim.

Reviewed against the official PostgreSQL 16 online manual on 2026-08-23 in Asia/Seoul (2026-08-22 UTC). The repository's hosted PostgreSQL test image remains separately immutably pinned by workflow digest; this reference records the major-version semantic contract rather than asserting a particular patch release is certified.