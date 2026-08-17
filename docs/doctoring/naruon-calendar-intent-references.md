# Naruon calendar intent technical references

## Status

Active-PR evidence only. Protected `develop` does not ship this integration until the owning PR integrates.

## Contract evidence

- ContextualWisdomLab. (2026). *Naruon calendar API contract* [Source code, revision `ddd05c5aaf3e170aa2bdc4412647b43b95d5a6b9`, `backend/api/calendar.py`]. GitHub. This exact revision defines `/api/calendar/writeback-intent`, customer-owned CalDAV source selection, intent provenance, If-Match handling, and optional provider execution consumed by ADR 0010.

## Authoritative protocol references

- Daboo, B., Desruisseaux, B., & Dusseault, L. M. (2007). *Calendaring extensions to WebDAV (CalDAV)* (RFC 4791). Internet Engineering Task Force. https://doi.org/10.17487/RFC4791
- Desruisseaux, B. (2009). *Internet calendaring and scheduling core object specification (iCalendar)* (RFC 5545). Internet Engineering Task Force. https://doi.org/10.17487/RFC5545
- Fielding, R., Nottingham, M., & Reschke, J. (2022). *HTTP semantics* (RFC 9110). Internet Engineering Task Force. https://doi.org/10.17487/RFC9110

## Use in Orgmetra

Orgmetra does not reimplement CalDAV or iCalendar. These references constrain the semantics expected from the Naruon-owned provider boundary, especially conditional-request behavior. Orgmetra's adapter stays transport-neutral and fail-closed, sends no provider credentials, and requests intent creation without provider execution until the foreign owner defect documented in ADR 0010 is repaired and revalidated.
