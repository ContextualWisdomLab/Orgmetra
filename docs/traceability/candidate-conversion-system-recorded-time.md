# Candidate conversion system-recorded-time traceability

## Protected-main truth

Protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` already separates candidate-worker conversion business time (`effective_from` / `effective_to`) from knowledge/system time (`recorded_from` / `recorded_to`) and defaults `recorded_from` to PostgreSQL transaction time. The pre-repair INSERT boundary nevertheless accepts an explicit caller-authored `recorded_from` when the broader hire/evidence chronology remains internally consistent.

## Active repair

PR #87 adds a forward migration, `database/migrations/0017_candidate_conversion_system_recorded_time.sql`, that requires every fresh `candidate_worker_conversion_record.recorded_from` to equal PostgreSQL `transaction_timestamp()` for the current transaction. It does not rewrite migration 0009 or historical rows.

The repair preserves these separate meanings:

- `effective_from`: business-effective date of the candidate-to-worker conversion;
- `recorded_from`: authoritative database transaction time at which Orgmetra learned/persisted the conversion;
- `recorded_to`: later system-time closure performed only through the existing bitemporal correction guard.

The existing candidate-conversion governance trigger remains authoritative for tenant-local candidate, Person, Employment, sealed selection decision, human confirmation, audit/outbox and correction provenance. The new trigger only closes the system-time authorship gap and intentionally runs before the broader governance trigger.

## RED → GREEN acceptance evidence

`tests/test_candidate_conversion_system_recorded_time_postgres.sh` constructs an otherwise-valid tenant-local hire decision with sealed evidence and immutable audit/outbox evidence. The RED head `9417a9783bc34ae39e82a9c1da4155b843ce5492` checked out in hosted run `32598511944`, job `97093082138`, and failed because an INSERT with `recorded_from = transaction_timestamp() - interval '2 minutes'` succeeded. The exact failure was `candidate conversion accepted caller-authored historical recorded_from`.

The repaired regression requires that same INSERT to fail with SQLSTATE `23514` and the dedicated system-time error, while a conversion that omits `recorded_from` must succeed and return `recorded_from = transaction_timestamp()` from the INSERT transaction.

## Ownership and scope

This is an Orgmetra-owned persistence repair. It does not change Keyverse, Naruon, contextual-orchestrator, Psychometrics Commons or any other dedicated-writer repository; it uses no cross-service application-table SQL and grants no new employment-decision authority.

## Status vocabulary

- Protected main: vulnerable system-time authorship boundary described above.
- Active PR #87: forward migration plus adversarial PostgreSQL regression.
- Release/certification: not claimed. Merge and release still require the repository's fresh CI/security/recovery/review gates on one integrated protected head.
