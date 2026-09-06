# Changelog

All notable package changes are recorded here.

## Unreleased

- Add a governed, aggregate-only `SelectionOutcomeMonitoringPlan` that binds one Job-scoped total selection process to exact aggregate population/outcome snapshots, protected-attribute handling, small-sample interpretation, statistical-plan provenance, a distinct accountable reviewer, and explicit human review without carrying candidate-level values or making an adverse-impact/legal determination.
- Follow Orgmetra's authoritative canonical non-sentinel operational UUID contract for `tenant_record_id`, while every packet-owned namespaced trust-bearing reference remains canonical non-sentinel UUIDv4 and rejects UUIDv1/non-v4, human-readable, value-bearing, sentinel, and noncanonical suffixes through construction and replacement paths.
- Require every packet reference to be re-resolved within the exact tenant through its authoritative boundary before actor separation, Job-scope verification, or accountable review, preventing cross-tenant evidence mixing behind valid opaque UUIDs.
- Bind a true positive `evidence_version` (1..2147483647) into canonical JSON and SHA-256 evidence so revisions to high-impact monitoring evidence cannot silently collide.
- Freeze `generated_at` to a detached built-in UTC instant at issuance, reject future generation times, normalize caller timezone-provider failures to fail-closed validation errors, and prevent later mutable `tzinfo` behavior from rewriting canonical monitoring evidence.
- Bind each live issued monitoring plan to its exact construction-time canonical bytes with a process-local HMAC seal stored outside packet-writable slots; seal registration is single-use per live identity, so a low-level valid-value rewrite followed by repeated `__post_init__()` cannot renew trust. Canonical export fails closed if evidence is rewritten, seal renewal is attempted, or process-local issuance evidence is unavailable. This is defense-in-depth only: durable uniqueness, authorization, and immutable audit/outbox remain authoritative host/persistence responsibilities.
- Require SHA-256 digest evidence to be exact built-in strings before regex validation and canonical binding, matching the package's strict runtime-type policy for other trust-bearing text and rejecting caller-defined `str` subclasses.
- Consolidate selection-monitoring quality into canonical Foundation CI: the retired package-local workflow stays absent, Foundation delegates to an isolated hash-locked package contract, and executable regression keeps 100% statement/branch coverage plus workflow non-resurrection under current protected ownership.
