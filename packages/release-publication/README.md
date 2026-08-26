# Orgmetra Release Publication

This package is the final **execution boundary**, not a development-agent release command. It consumes one factory-issued `ReleaseAuthorizationReceipt` from the governed parent boundary and delegates publication to a host-owned `ReleasePublicationPort`.

The boundary is intentionally fail-closed:

- the parent authorization must still be exact, sealed, `not_published`, and no more than 60 seconds past its immutable authorization audit when publication begins;
- a production publisher must resolve the exact authorization digest at its durable side-effect boundary and refuse to create the release after that same 60-second authorization window; Orgmetra also refuses to bless host evidence whose `published_at` falls after expiry;
- the publication correlation is a packet-owned opaque UUIDv4 reference;
- `publish_release(...)` is called **at most once** for one invocation;
- if the host response is lost, malformed, or scope-mismatched, Orgmetra performs `reconcile_release(...)` lookup only and never republishes;
- unresolved ambiguity raises `ReleasePublicationIndeterminateError` with an explicit **do not republish** contract;
- accepted host evidence must bind the exact parent-authorization SHA-256, candidate Git revision, tag, publication correlation, platform release digest, immutable audit-envelope digest, and publication timestamp;
- the returned `ReleasePublicationReceipt` is factory-issued, redacted in routine repr, canonically hashed, and detects post-issuance mutation.

`ReleasePublicationPort` is a host adapter contract. A production adapter must make the **authorization evidence digest** a durable uniqueness/precondition key, keep the publication correlation idempotent at the release platform, enforce authorization expiry before the external write, preserve exact candidate/tag preconditions, durably bind publication audit evidence, and implement reconciliation as read-only lookup. This package does not contain GitHub credentials, does not use administrator bypass, and does not itself create a tag or GitHub Release during development or tests.

## Dependency and release order

This package is stacked after governed readiness review and exact-revision release authorization. The development PR must remain non-authorizing until its parent integrates and all applicable current-head local and central gates execute again against fresh `develop`. Actual release/version/tag creation is allowed only from one exact integrated head after the repository's acquisition-grade review, security, coverage, package, provenance, recovery, accessibility, migration/rollback and operational gates pass together without routine administrator bypass.
