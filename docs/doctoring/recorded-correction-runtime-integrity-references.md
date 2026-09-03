# Recorded-correction runtime integrity references

## Evidence use

These primary technical references support the active Orgmetra recorded-correction runtime-integrity repair. They justify the implementation facts that `dataclasses.replace(...)` creates an object of the same runtime dataclass type and that Python subclasses may define special comparison behavior. They do not constitute a certification claim or substitute for Orgmetra's executable regressions.

## APA 7 references

Python Software Foundation. (2026). *dataclasses — Data classes* (Python 3.14.7 documentation). https://docs.python.org/3/library/dataclasses.html

Python Software Foundation. (2026). *datetime — Basic date and time types* (Python 3.14.7 documentation). https://docs.python.org/3/library/datetime.html

Python Software Foundation. (2026). *Classes* (Python 3.14.7 documentation). https://docs.python.org/3/tutorial/classes.html

## Design implications recorded for Orgmetra

- `dataclasses.replace(obj, **changes)` creates a new object of the same type as `obj`; therefore structural acceptance of an arbitrary caller-owned dataclass can propagate that foreign runtime type through a correction helper rather than converting it into an authoritative kernel fact.
- Python's object model permits user-defined classes and subclasses to supply special comparison behavior. A trust-bearing chronology boundary therefore establishes the expected runtime primitive before invoking ordering operations on caller-supplied values.
- This repair intentionally uses exact runtime-type checks only at the authoritative evidence/correction boundary. It is not a general prohibition on Python polymorphism elsewhere in Orgmetra.
