# ADR 0022: Govern compensation changes before authoritative mutation

- Status: Proposed (active PR only)
- Date: 2026-08-19

## Context

Compensation changes are high-impact employment actions. A useful enterprise review boundary must correlate the proposed change to authoritative worker scope, the exact current/proposed compensation artifacts, the governing policy, pay-equity review, budget authorization, and payroll handoff without copying salary, wage, bonus, benefit, equity, protected-attribute, or free-form case values into portable evidence.

Syntactically valid Person, Employment, Assignment, policy, actor, or compensation-artifact references do not prove tenant membership, worker scope, policy applicability, actor separation, or effective-date correctness. Opaque identifiers also remain sensitive correlating metadata even when direct identifiers and pay values are absent. The authoritative HRIS already owns tenant identity semantics: protected Orgmetra core accepts canonical non-sentinel operational UUIDs, including UUIDv7. This leaf package therefore must not narrow `tenant_record_id` to UUIDv4. UUIDv4 remains appropriate for packet-owned opaque references where this package owns the correlation-privacy contract.

Recorded-time evidence also crosses an ownership boundary. Python permits a caller to attach a custom `tzinfo` object to an otherwise exact built-in `datetime`; that timezone object can be mutable. Retaining it inside an issued review packet would allow later caller-side state changes to rewrite the apparent UTC instant or invalidate the packet's creation-time digest. The packet therefore must resolve the input offset exactly once and retain only a detached built-in UTC `datetime` as its trust-bearing recorded-time value.

Current primary-source context is recorded in `docs/doctoring/compensation-change-review-references.md`. ISO 30414:2025 provides current human-capital reporting/disclosure context; U.S. EEOC compensation guidance demonstrates why compensation governance must not turn protected-attribute review into uncontrolled evidence copying; U.S. Department of Labor FLSA recordkeeping guidance demonstrates the need for accountable wage/time records. These are governance inputs only, not certification or universal legal-compliance claims.

## Decision

Orgmetra will expose a value-minimized `CompensationChangeReviewPacket` before any authoritative compensation-related HRIS mutation or payroll execution.

The packet binds one authoritative Orgmetra `tenant_record_id` that satisfies the protected-core canonical non-sentinel operational-UUID contract. Packet-owned opaque references for the compensation review, Person, Employment, active Assignment/Job/Position snapshot, current compensation snapshot, proposed compensation plan, compensation policy, pay-equity review, budget authorization, payroll handoff plan, requester, and reviewer remain canonical non-sentinel UUIDv4-backed namespaced references. This preserves interoperability with authoritative UUIDv7 tenant identities while preventing timestamp/node-derived correlation metadata from entering packet-owned references presented as opaque. Evidence artifacts carry independent lowercase SHA-256 digests; a bounded positive `evidence_version`, proposed business effective date, and precision-preserving recorded-time instant are part of canonical evidence.

`generated_at` accepts only an exact built-in timezone-aware `datetime`. Construction obtains a concrete UTC offset once, fails closed when the offset is indeterminate, converts the wall time to the corresponding instant, and stores a detached exact built-in UTC `datetime` backed by `datetime.timezone.utc`. Canonical export therefore never depends on later mutation of a caller-owned timezone object. Datetime subclasses are rejected so caller-overridable conversion or formatting methods cannot forge recorded-time evidence.

The packet deliberately excludes compensation values, protected-attribute values, free-form case narrative, credentials, and free-form model output. It explicitly acknowledges remaining personal-data correlation with `contains_personal_data = true`.

Direct construction and replacement fail closed unless the packet remains:

- `human_confirmation_required = true`;
- `decision_authority = human_review_only`;
- `review_state = requires_human_review`;
- `scope_verification_state = requires_authoritative_resolution`;
- `mutation_state = not_authorized_to_apply`; and
- `external_execution_state = not_authorized_to_execute`.

Requester and reviewer opaque references must differ, but authoritative separation of duties requires both identities to be re-resolved inside the packet tenant immediately before approval. The host must also re-resolve every packet reference, prove Person-to-Employment and active Assignment/Job/Position scope, and verify the current compensation snapshot, proposed plan, exact compensation policy, pay-equity review, budget authorization, effective date, and payroll-handoff provenance without copying compensation or protected-attribute values into the packet. Neither authoritative tenant UUID syntax nor packet-owned UUIDv4 syntax proves tenant membership, actor identity, worker scope, policy applicability, or substantive correctness.

Any authorized HRIS change must use the authoritative Orgmetra People boundary with its own purpose-bound authorization, idempotency, bitemporal persistence, and immutable audit/outbox evidence. Payroll execution remains behind the payroll owner's published contract. This package performs no foreign mutation and no direct cross-service application-table SQL.

## Consequences

### Positive

- A review envelope cannot masquerade as compensation approval, an applied HRIS change, or completed payroll execution.
- Buyers can correlate exact policy/equity/budget/proposed-plan evidence while minimizing duplicated pay and protected-attribute values.
- Authoritative UUIDv7 tenant identities remain interoperable instead of being rejected by a leaf-only UUIDv4 policy.
- UUIDv1 timestamp/node correlation remains excluded from packet-owned namespaced trust references.
- Changes to governed evidence or `evidence_version` change the canonical packet digest.
- Recorded-time evidence is detached from caller-owned mutable timezone state before issuance, so a previously issued canonical payload cannot drift because an input timezone object later changes.
- Cross-tenant, wrong-worker, stale-policy, actor-separation, and effective-date questions remain explicit authoritative-resolution obligations instead of being inferred from reference syntax.

### Trade-offs

- The packet is not anonymous; opaque worker/evidence correlations still require purpose-bound access, retention, export, and audit controls.
- UUID syntax is not authorization, ownership, or relationship evidence; authoritative tenant identity policy and packet-owned reference privacy are intentionally separate ownership boundaries.
- A pay-equity evidence reference/digest proves which artifact was reviewed, not that compensation is fair, nondiscriminatory, or legally sufficient.
- The packet does not calculate compensation, payroll, taxes, protected-class statistics, pay-equity findings, or legal conclusions.
- Hosts must perform authoritative scope and actor resolution at approval time.
- The stored recorded-time representation is normalized to UTC; an input timezone's display-zone identity is intentionally not retained as trust-bearing evidence.

## Verification

The package requires exact 100% owned statement and branch coverage; beginner-readable module/class/callable docstrings; direct-construction and `dataclasses.replace(...)` fail-closed regressions; authoritative tenant interoperability with the protected-core canonical non-sentinel operational-UUID contract, including the canonical UUIDv7 tenant used by the core PostgreSQL regression and rejection of RFC 9562 Nil/Max sentinels; strict UUIDv4 packet-owned namespaced references including UUIDv1 rejection; lowercase SHA-256 evidence; redacted `repr`; closed non-sensitive reason categories; bounded evidence versions; business-date validation; exact built-in timezone-aware timestamp validation; one-time offset resolution with detached UTC storage; indeterminate-offset and datetime-subclass rejection; mutable-timezone post-issuance regression; deterministic canonical JSON/digest evidence; separate requester/reviewer references plus explicit authoritative identity re-resolution; and immutable human-review/no-mutation/no-execution states.
