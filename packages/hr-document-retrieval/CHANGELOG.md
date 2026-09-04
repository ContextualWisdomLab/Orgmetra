# Changelog

## 0.1.0 — 2026-08-25

- Add a purpose-bound HR document retrieval execution boundary with fresh authoritative metadata resolution, exact human-accountable authorization, bounded artifact reads, SHA-256 verification, and immutable audit-before-release semantics.
- Recheck authorization freshness after the protected artifact read and after the audit append immediately before byte release, and use the post-verification instant as the retrieval receipt's system-recorded time.
- Keep returned document bytes usable for authorized HR work while excluding content and high-value HR data from durable retrieval receipts.
- Fail closed on tenant/document/scope drift, authorization that expires before release, denied authorization, retention/classification drift, hostile runtime primitives, oversized or digest-mismatched artifacts, and audit persistence failure.
- Add adversarial tests and a dedicated exact-head quality workflow requiring 100% owned production statement/branch coverage, a hash-bound isolated package-install smoke test, and a clean checkout.
- Bound public Python support to the exact hosted 3.14 minor (`>=3.14,<3.15`) and pin the quality lane to CPython 3.14.7 rather than claiming untested 3.12/3.13 or future minor compatibility.
- Make the isolated-install smoke test reproducible by installing the reviewed, SHA-256-locked setuptools 84.0.0 wheel before invoking the package's declared `setuptools.build_meta` backend with build isolation disabled.
- Build the tested package wheel from the exact checkout, compute that wheel's SHA-256, and require the same local wheel hash during isolated installation rather than allowing an unhashed source-install command.
