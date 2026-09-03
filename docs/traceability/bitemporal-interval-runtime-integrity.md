# Bitemporal interval runtime integrity

## Protected-main truth

At `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`, the shared `DateInterval` and `RecordedInterval` boundaries enforce interval ordering and some timezone presence checks but accept caller-controlled subclasses of Python `date`/`datetime`. Recorded time also treats non-null `tzinfo` as sufficient even when `utcoffset()` is `None`.

Those behaviors are unsafe for authoritative HRIS reconstruction because effective-time and system-recorded-time visibility are trust-bearing decisions. A polymorphic temporal object must not control comparison or rendering behavior at that boundary.

## Active PR #69

PR #69 changes only Orgmetra-owned HRIS-kernel interval validation plus adversarial regressions and this supporting traceability/doctoring evidence.

The active repair requires:

- exact built-in `date` for stored effective bounds and effective-date query coordinates;
- exact built-in `datetime` for stored recorded bounds and knowledge-cutoff query coordinates;
- a usable non-`None` UTC offset rather than `tzinfo` presence alone;
- stable `IntervalError` normalization when a hostile/custom timezone implementation fails during offset resolution;
- unchanged half-open interval, ordering, overlap and existing business semantics.

RED evidence began at `f425c3878b923e6e626d79617d82377ebf77d235` and was strengthened at `2b37ad4e8ac2cb6337d8e2e69f9ca39175d0d207`. Root-cause implementation is `827342a9a1ff102942584a574c81ca4b61bb0c31`; `e0e4e677dffd4285dea39bdd51509d599085d100` covers hostile timezone failure normalization.

## Accepted architecture preserved

This repair does not change the repository's accepted bitemporal model: effective/business time remains separate from system-recorded time; intervals remain half-open; corrections remain append/close rather than in-place history rewriting.

## Out of scope

This lane does not introduce a timezone-provider allowlist, change storage types, alter Job/Position/Assignment ownership, mutate any dedicated-writer dependency, or claim legal/compliance certification.

## Primary source

See `docs/doctoring/bitemporal-interval-runtime-references.md` for the APA 7 record and source interpretation.
