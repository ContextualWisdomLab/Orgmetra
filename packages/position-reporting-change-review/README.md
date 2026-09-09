# Orgmetra Position Reporting Change Review

`orgmetra-position-reporting-change-review` is a transport-neutral, pre-mutation governance contract for reviewing a change to one solid-line Position-to-Position reporting relationship.

## Protected-main truth and scope

Protected `develop` keeps Job, Position and Assignment as separate HRIS concepts but does not yet ship an authoritative reporting-line mutation service. An active Position-reporting hierarchy PR adds read-only bitemporal relationship reconstruction; this package does not import it, depend on its branch, or treat active-PR behavior as protected-main truth.

The review packet binds an authoritative tenant, subordinate Position, current manager Position, proposed manager Position, requested business-effective date, exact Position/organization scope digests, controlled reason, requester, reviewer, evidence version and system-recorded time. It contains no Person identifier, worker value, compensation, performance rating, free-form reason or LLM decision.

## What happens next

A valid packet is **not permission to change HRIS data**. Before any reporting-line mutation, the host must re-resolve the three Position records and the current solid-line relationship in the exact tenant at `effective_on` and the current system-recorded cutoff; prove the Positions are valid and staffable; prove requester/reviewer authoritative identity separation; reject self-reporting, cycles and multiple visible solid-line managers; verify the reviewed evidence digests and reason; and only then invoke the future authoritative mutation boundary with immutable audit/outbox evidence.

The package performs no database write, no direct cross-service application-table SQL, no identity-provider mutation and no autonomous employment decision.

## Identifier and evidence rules

- `tenant_record_id` follows the protected HRIS canonical non-sentinel operational UUID contract, including UUIDv7.
- Position references use `position_record:<canonical operational UUID>` so the leaf package does not duplicate a UUIDv4-only rule over HRIS-owned records.
- The packet-owned `position_reporting_change:` reference and `actor:` review correlations require canonical UUIDv4.
- Position and organization scope snapshots are bound by lowercase SHA-256 digests rather than copied values.
- `effective_on` is business time. `recorded_at` is the system-recorded evidence instant and is canonicalized to UTC RFC 3339 text.
- `mutation_state=not_authorized_to_apply`, `scope_verification_state=requires_authoritative_resolution`, and `decision_authority=human_review_only` are fail-closed constants.

## Quality evidence

The dedicated workflow builds the exact wheel from the PR head, installs it through a SHA-256-bound requirement, runs the installed artifact on pinned CPython 3.14.7, requires exact 100% owned statement/branch coverage, and leaves the checkout clean. Repository-level tests require ADR, doctoring and traceability-only edits to trigger the same gate.
