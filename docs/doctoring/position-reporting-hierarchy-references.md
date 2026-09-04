# Position reporting hierarchy references

Checked 2026-08-23. These sources inform the active PR #94 design without claiming that an external standard mandates Orgmetra's exact internal schema.

## Primary and authoritative sources

HR Open Standards Consortium. (2026). *About HR Open*. https://www.hropenstandards.org/about-hr-open

- HR Open describes its specifications as voluntary consensus standards for human-resource-related data exchange and interoperability. Orgmetra therefore keeps the new reporting contract modular and does not bind internal Position reporting truth to a vendor-specific worker-manager payload. This source does **not** establish that a particular `reports_to` field or table is mandatory.

Python Software Foundation. (2026). *datetime — Basic date and time types* (Python 3.14 documentation). https://docs.python.org/3.14/library/datetime.html

- The official `datetime` contract states that timezone-aware behavior delegates to `tzinfo.utcoffset()` and that an unknown offset may be represented by `None`. The reporting snapshot boundary therefore resolves the caller-owned offset once, normalizes it to a built-in UTC instant, and fails closed when the offset is absent or resolution raises, instead of repeatedly executing caller-owned timezone behavior during bitemporal comparisons.

## Internal design constraint

Protected Orgmetra architecture is the authoritative source for the distinction among Job, Position and Assignment. PR #94 adds only the missing Position-to-Position solid-line relationship reconstruction. It does not infer a manager Person from an Assignment and does not reinterpret organization-unit parentage as supervisory authority.