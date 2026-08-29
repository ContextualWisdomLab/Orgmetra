# Recorded-correction runtime integrity traceability

## Scope

This note traces the bounded Orgmetra HRIS-kernel repair proposed on the active `fix/governed-recorded-correction-boundary` branch. It does not describe protected-main behavior as already shipped.

## Protected-main truth

The protected snapshot used to establish the defect is `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`, committed at 2026-08-21 01:56:37 UTC (2026-08-20 18:56:37 at the commit's UTC-07:00 author offset). It is a descendant of the earlier protected snapshot `e7ddb7a78a5e1460410005d10f43ebf18c5e12e4`, committed at 2026-08-20 15:26:50 UTC (08:26:50 at UTC-07:00). The earlier snapshot is lineage only; the defect statement below is scoped to `9e3e4847510e1e612b48474ba42b177b8ed824df`.

At that protected snapshot, `close_recorded_interval(...)` is the bitemporal correction helper. The protected implementation accepts any dataclass-like value whose `recorded` attribute is a `RecordedInterval`, then compares caller-provided `recorded_to` before constructing the replacement interval. Because Python permits subclasses to override special comparison methods, that boundary can execute caller-controlled ordering behavior before chronology is trusted.

## Active-PR contract

The active repair requires, before attribute access or temporal comparison:

1. the corrected object has exactly one of the four authoritative runtime types: `EmploymentVersion`, `OrganizationUnitVersion`, `PositionVersion`, or `AssignmentFact`;
2. its recorded history is exactly the governed `RecordedInterval` runtime type with exact built-in `datetime` endpoints; and
3. the requested close instant is exactly the built-in `datetime` runtime type.

Only then may the existing rules run: the current recorded interval must still be open and `recorded_to` must be strictly later than `recorded.start`. The function still changes only the recorded interval and returns a dataclass replacement; business columns remain unchanged.

## RED-to-repair evidence

- RED `d24f940a5f81a829419253dbbe9f768293643c2b`: a caller-owned dataclass with a valid-looking `recorded` field and a hostile `datetime` subtype must not cross the authoritative correction boundary.
- Repair `739e26581095fedd0a18335f2311f972f6b13507`: establish exact governed runtime types before `dataclasses.replace(...)` or chronology comparison.
- Coverage strengthening `efd87f45417031662382b0c901110f19206488d5`: exercise the fail-closed malformed recorded-history branch on an exact kernel fact.
- Endpoint hardening `cbc6dfb374e8ae43df0cadce39aab44dc78fec94`: require exact built-in `datetime` values for both recorded endpoints before chronology comparison, closing the hostile-start-subclass gap found during review.

## Buyer and control relevance

Recorded-time correction is part of reconstructing what the HRIS knew at a given system time. Accepting structural lookalikes or caller-defined comparison semantics would make the correction helper capable of emitting a value that appears kernel-governed even though its type or chronology was not authoritative. The repair keeps correction-not-rewrite semantics while narrowing the trust boundary; it does not add a new employment decision path and does not call any CWL dependency repository.

## Evidence status

The code and regressions are implemented on the active PR only. Repository-owned exact-head Foundation, People, Job-Analysis, Workforce, PostgreSQL, SAST, Security, and Recovery evidence was terminal GREEN before this documentation repair. This documentation commit creates a new exact head, so predecessor-head success does not transfer: every applicable repository and central required workflow must be regenerated or freshly verified on the resulting head. Independent non-author approval remains a separate merge gate.
