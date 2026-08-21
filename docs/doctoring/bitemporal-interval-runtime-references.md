# Bitemporal interval runtime-integrity references

## Scope

This note records the primary technical source used for the Orgmetra HRIS-kernel interval runtime-integrity repair. It supports implementation reasoning only and is not a certification or standards-conformance claim.

## Primary technical documentation

Python's `datetime` documentation distinguishes aware and naive `datetime` values by both a non-`None` `tzinfo` and a non-`None` UTC offset. It also documents the `date` → `datetime` subclass relationship and notes that subclass comparison behavior can be overridden. Orgmetra therefore treats caller-controlled temporal subclasses as untrusted boundary input and checks a usable UTC offset before system-time ordering.

## APA 7 reference

Python Software Foundation. (2026). *datetime — Basic date and time types* (Python 3.13.15 documentation). https://docs.python.org/3.13/library/datetime.html

## Evidence status

- Protected-main defect coordinate: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`.
- Active repair PR: #69.
- Research-only claim: none; the source is used for runtime semantics, not psychometric or legal inference.
