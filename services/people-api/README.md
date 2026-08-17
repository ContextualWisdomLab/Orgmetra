# Orgmetra People API

This directory is the rebuilt customer-facing People API boundary on the current protected Orgmetra contracts. The historical PR implementation is retained in Git history but is not replayed because it carried a legacy tenant schema, mutable audit shape, duplicated domain kernel, and pre-governance candidate-worker link.

The current bounded slice owns request-edge bearer-token parsing and an injected token-authentication protocol. It deliberately does **not** encode HR purpose grants in the authenticated principal. Protected field access is delegated to the integrated Orgmetra `orgmetra_keyverse_adapter` purpose-bound policy contract, which binds active tenant, actor tenant, resource tenant, exact opaque target reference, purpose, operation, operation-specific scope, and requested field set before protected HR values may be returned.

Next implementation work on this same branch should add the HTTP route and repository ports against the protected HRIS kernel, governed candidate-worker conversion, bitemporal employment records, and governed audit/outbox transaction without restoring the superseded persistence model.
