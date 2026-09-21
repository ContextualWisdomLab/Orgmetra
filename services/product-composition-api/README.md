# Orgmetra product composition

This service package is the first executable slice of Orgmetra's product-composition boundary tracked by #432. It validates whether configured product routes refer to exact immutable owner API releases before those routes can become product-ready.

It does **not** authenticate Keyverse tokens, bind identity subjects to People records, authorize HR resources, proxy HTTP traffic, own retry/idempotency truth, query bounded-context databases, or make HR/scientific decisions. Those authorities remain with their existing owners. A successful admission receipt proves only that the configured route coordinates match the observed released owner contract evidence supplied by the trusted composition host.

Current scope is deliberately transport-neutral. The package can sit behind a future released shared edge runtime or another approved ingress without changing its contract. Mutable branches, floating release labels, copied owner schemas, reachability-only checks and digest-only pointers do not qualify as route admission.

Production completion still requires released Keyverse consumer evidence, Orgmetra identity ACLs, downstream owner OpenAPI releases, an executable HTTP composition host, failure/recovery/rollback evidence, deployment provenance, and full buyer-path performance verification.
