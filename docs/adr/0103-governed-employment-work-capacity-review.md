# ADR 0103: Governed Employment work-capacity review

- Status: proposed on active PR; not protected-main truth until merged.
- Date: 2026-08-24

## Context

Protected `develop` separates Employment from Assignment and already constrains one Employment's visible Assignment allocation portfolio. It does not yet expose a bounded evidence object for reviewing a proposed change to the Employment's overall contracted work capacity before authoritative mutation. Conflating Employment capacity with Assignment allocation would blur two different facts: how much contractual/work capacity the Employment represents versus where that capacity is allocated.

ISO/TS 30425:2021 publicly describes workforce availability as concerning the working capacity of permanent and temporary workforces while distinguishing that concept from existing allocated work, skills, or suitability. ISO 30414:2025 identifies workforce composition as a human-capital reporting area. Orgmetra uses those public scope statements only as design evidence; it does not reproduce licensed formulas or claim standards conformity.

## Decision

Create an Orgmetra-owned `EmploymentWorkCapacityReviewPacket` that binds a proposed change to one authoritative Employment and keeps it explicitly non-authoritative.

The packet records current/proposed capacity ratios in exact four-decimal `[0, 1]` form, one business-effective date, SHA-256 evidence for reviewed employment terms, enterprise capacity policy/definition, and reviewer identity resolution, distinct requester/reviewer correlations, controlled reason, evidence version, human review time, and an Orgmetra-generated system-recorded UTC issuance time. Callers cannot supply or backdate `recorded_at`.

The packet shall not mutate or authorize Employment, Assignment, compensation, payroll, leave, or scheduling. It shall not infer legal full-time/part-time classification, worker suitability, or availability for specific work. The authoritative mutation boundary must re-resolve current tenant/Employment truth, reviewer authority, reviewed evidence, Assignment implications, and compensation/payroll implications and then persist the bitemporal change with immutable audit/outbox evidence atomically.

## Data and privacy consequences

No Person name, email, phone, address, salary, rating, free-form personal text, credential, prompt, or model output is retained in canonical evidence. Operational HRIS identifiers remain opaque references. Actor correlations are packet-owned UUIDv4 references. Canonical export is deterministic and routine representations are redacted.

## Integrity consequences

Trust-bearing scalars require exact runtime types before validation. Nil/Max UUID sentinels, malformed digests, noncanonical capacity scale, signed negative zero, no-op changes, actor overlap, future human review relative to system issuance, mutable governance constants, and post-issuance field mutation fail closed. System-recorded time is generated at the owner boundary rather than trusted from a caller. The process-local issuance seal is defense in depth only; durable authorization and uniqueness remain host/audit responsibilities.

## Alternatives rejected

- **Use Assignment allocation as Employment capacity.** Rejected because allocation is where capacity is used, not the capacity of the Employment itself.
- **Store weekly hours as a universal legal truth.** Rejected because legal and contractual semantics vary; this slice binds an enterprise-defined normalized ratio and the exact reviewed policy digest instead.
- **Let callers supply system-recorded time.** Rejected because it permits backdated knowledge-time evidence; business/effective time and human review time are separately modeled inputs, while system-recorded issuance is owned by Orgmetra.
- **Allow the packet to apply the change.** Rejected because changing work capacity can affect employment terms, allocation, compensation, and payroll and therefore requires authoritative human-reviewed resolution and immutable audit evidence.
