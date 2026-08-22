# Recorded-correction runtime integrity traceability

## Scope

This note traces the bounded Orgmetra HRIS-kernel repair proposed on the active `fix/governed-recorded-correction-boundary` branch. It does not describe protected-main behavior as already shipped.

## Protected-main truth

Protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` exposes `close_recorded_interval(...)` as the bitemporal correction helper. The protected implementation accepts any dataclass-like value whose `recorded` attribute is a `RecordedInterval`, then compares caller-provided `recorded_to` before constructing the replacement interval. Because Python permits subclasses to override special comparison methods, that boundary can execute caller-controlled ordering behavior before chronology is trusted.

## Active-PR contract

The active repair requires, before attribute access or temporal comparison:

1. the corrected object has exactly one of the four authoritative runtime types: `EmploymentVersion`, `OrganizationUnitVersion`, `PositionVersion`, or `AssignmentFact`;
2. its recorded history is exactly the governed `RecordedInterval` runtime type; and
3. the requested close instant is exactly the built-in `datetime` runtime type.

Only then may the existing rules run: the current recorded interval must still be open and `recorded_to` must be strictly later than `recorded.start`. The function still changes only the recorded interval and returns a dataclass replacement; business columns remain unchanged.

## RED-to-repair evidence

- RED `d24f940a5f81a829419253dbbe9f768293643c2b`: a caller-owned dataclass with a valid-looking `recorded` field and a hostile `datetime` subtype must not cross the authoritative correction boundary.
- Repair `739e26581095fedd0a18335f2311f972f6b13507`: establish exact governed runtime types before `dataclasses.replace(...)` or chronology comparison.
- Coverage strengthening `efd87f45417031662382b0c901110f19206488d5`: exercise the fail-closed malformed recorded-history branch on an exact kernel fact.

## Buyer and control relevance

Recorded-time correction is part of reconstructing what the HRIS knew at a given system time. Accepting structural lookalikes or caller-defined comparison semantics would make the correction helper capable of emitting a value that appears kernel-governed even though its type or chronology was not authoritative. The repair keeps correction-not-rewrite semantics while narrowing the trust boundary; it does not add a new employment decision path and does not call any CWL dependency repository.

## Evidence status

The code and regressions are implemented on the active PR only. Hosted exact-head Foundation, People, Job-Analysis, Workforce, SAST, Security, and Recovery evidence must be terminal GREEN before the PR can leave Draft. Independent non-author review remains a separate merge gate.
