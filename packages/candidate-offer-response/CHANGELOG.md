# Changelog

## 0.1.0 - Unreleased

- Add candidate-originated `offer_accepted` / `offer_declined` evidence bound to exact offer approval and offer-terms digests.
- Require candidate actor and identity-resolution provenance while keeping Keyverse read-only.
- Preserve the published identity-owner contract by accepting a bounded namespaced opaque `candidate_actor_reference` instead of imposing an Orgmetra-invented UUIDv4 requirement on the external actor identity.
- Keep every response explicitly non-authorizing for hire, employment, compensation execution, or candidate-to-worker conversion.
- Exclude candidate PII, compensation values, free-form decline reasons, credentials, and model output from the evidence packet.
- Normalize recorded/responded instants to detached built-in UTC values, reject trust-bearing runtime subclasses, redact `repr`, and detect post-construction evidence rewriting.
- Bind canonical export to the exact snapshot that passed issuance-seal validation so an interleaving valid-value rewrite cannot become emitted audit evidence after the integrity check.
- Add exact 100% statement/branch coverage and exact-head CI for the owned package.
- Build a wheel and execute the quality suite against the SHA-256-bound installed artifact in a fully isolated virtual environment; install the reviewed hash-pinned pytest/coverage toolchain inside that environment and fail closed if package or test-tool imports resolve outside it.
- Retire the package-specific quality workflow after protected repository-workflow consolidation; preserve the same SHA-256-bound installed-wheel and isolated-toolchain contract inside the canonical one-job Foundation CI lane.
