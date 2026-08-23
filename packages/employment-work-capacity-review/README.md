# Employment Work Capacity Review

This package creates a **human-reviewed, non-authoritative** evidence packet for a proposed change to one Employment's contracted work-capacity ratio.

It is deliberately separate from Assignment allocation. Assignment says where an Employment is allocated; this packet records evidence that an accountable human reviewed a proposed change in the Employment's overall capacity before any authoritative bitemporal mutation.

## What the packet binds

- the tenant and authoritative Employment reference;
- current and proposed capacity ratios, both as exact four-decimal `Decimal` values from `0.0000` through `1.0000`; signed negative zero is rejected so zero has one canonical evidence representation;
- the business-effective date;
- SHA-256 evidence for reviewed employment terms, the enterprise capacity policy/definition, and reviewer identity resolution;
- distinct requester and reviewer correlations;
- one controlled, non-sensitive reason code;
- evidence version and human review time;
- an Orgmetra-generated system-recorded UTC issuance time. Callers cannot supply or backdate `recorded_at`.

## What it does not do

The packet does **not** modify Employment, Assignment, compensation, payroll, leave, or scheduling. It does not decide whether a worker is legally full-time or part-time, does not infer suitability or availability for work, and carries no name, email, phone, salary, rating, free-form personal text, credential, prompt, or model output.

Before applying a reviewed change, the authoritative Orgmetra host must re-resolve the exact tenant and Employment, current capacity truth at `effective_on`, reviewer authority, employment-terms and capacity-policy evidence, Assignment-allocation implications, and compensation/payroll implications, then write the approved bitemporal change and immutable audit/outbox evidence atomically.

## Evidence integrity

Trust-bearing text and numeric values require exact built-in runtime types before parsing or comparison. Operational HRIS identifiers reject Nil/Max UUID sentinels without forcing a leaf UUID version; packet-owned actor correlations use opaque UUIDv4 references. Capacity ratios are finite, bounded, exact four-decimal non-negative representations with signed negative zero rejected. `reviewed_at` is caller-supplied human-review time, while `recorded_at` is created inside the Orgmetra constructor from the built-in UTC clock and must not precede that review. Canonical evidence is deterministic and routine `repr()` is fully redacted. A process-local weak issuance registry detects post-issuance field mutation before canonical export; it is defense in depth, not a durable signature or authorization system.

The package's dedicated GitHub workflow builds the exact wheel, binds installation to the wheel SHA-256, executes the installed artifact, requires exact 100% owned statement/branch coverage, and requires a clean checkout.
