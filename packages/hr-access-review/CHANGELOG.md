# Changelog

## 0.1.0 — Unreleased

- Add value-minimized `HrAccessReviewPacket` evidence for retaining, reducing, or removing existing HR access.
- Require an independent reviewer and exact tenant/scope/policy/entitlement provenance.
- Use packet-local pseudonymous `actor:` UUIDv4 correlations so durable review evidence cannot directly persist names, employee numbers, or raw identity-provider subject identifiers; live identity remains an authoritative external resolution concern.
- Bind reviewer identity-resolution evidence, the fixed `hr_access_recertification` purpose, and distinct human-review/system-recorded UTC times; reject system-recorded evidence that predates the review.
- Keep every packet non-enforcing with authoritative re-resolution required before any access mutation.
- Reject hostile runtime subclasses and post-construction evidence rewrite.
- Return the exact payload checked by the issuance digest so canonical export cannot race with a valid field rewrite.
- Add exact-head CI requiring an installable package artifact, 100% owned statement and branch coverage, and a clean checkout.
- Run installed-wheel tests in a fully isolated virtual environment whose pytest/coverage toolchain is installed from the reviewed hash-pinned repository dependency set; fail closed if the package or those test dependencies resolve outside that environment.
