# Changelog

## 0.1.0 — 2026-08-25

- Add a purpose-bound HR document retrieval execution boundary with fresh authoritative metadata resolution, exact human-accountable authorization, bounded artifact reads, SHA-256 verification, and immutable audit-before-release semantics.
- Recheck authorization freshness after the protected artifact read and immediately before audit/byte release, and use that post-verification instant as the retrieval receipt's system-recorded time.
- Keep returned document bytes usable for authorized HR work while excluding content and high-value HR data from durable retrieval receipts.
- Fail closed on tenant/document/scope drift, authorization that expires before release, denied authorization, retention/classification drift, hostile runtime primitives, oversized or digest-mismatched artifacts, and audit persistence failure.
- Add adversarial tests and a dedicated exact-head quality workflow requiring 100% owned production statement/branch coverage, an isolated package-install smoke test, and a clean checkout.
