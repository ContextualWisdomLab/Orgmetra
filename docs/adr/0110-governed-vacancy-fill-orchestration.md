# ADR 0110: Govern vacancy fill before authoritative Assignment mutation

- Status: active PR
- Decision date: 2026-08-24
- Protected-main baseline: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`

## Context

Protected main already exposes an authoritative, purpose-bound Assignment create path with tenant isolation, high-impact confirmation, evidence versioning, seat-capacity checks, idempotency, and atomic audit/outbox persistence. A buyer-facing vacancy workflow still needs an application boundary that proves the requested Position remains staffable and has enough allocation immediately before the Assignment write. UI or cached vacancy state must not become mutation authority.

## Decision

Add an Orgmetra-owned `fill_position_vacancy(...)` orchestration boundary in People API.

1. Validate exact runtime primitives on the proposed `AssignmentMutationCommand` before authorization or protected resolution.
2. Authorize the exact Assignment target before an injected vacancy authority may inspect protected staffing truth.
3. Require the vacancy authority to re-resolve the exact tenant, Employment, Person, Position, effective date, human confirmation, evidence version, staffable Position state, and available allocation.
4. Treat the verification as evidence only. Delegate the unchanged command to `create_assignment_record(...)`, which independently authorizes again immediately before the authoritative mutation port persists Assignment truth with existing audit/outbox and capacity controls.
5. Keep names, compensation, assessments, model output, and free-form review text outside the verification object.
6. Redact routine representation of the verification object.

This slice fills a vacancy through authoritative Assignment truth. It does not implement Position freeze/correction; that remains a separate future mutation contract rather than overloading Assignment semantics.

## Consequences

- Wrong-purpose callers cannot use the vacancy resolver as a protected staffing-data oracle.
- Stale UI vacancy state cannot authorize a write.
- A verification that drifts in tenant, worker, Position, effective date, review evidence, or available allocation fails closed before persistence.
- The final Assignment mutation retains the existing source-of-truth, idempotency, audit/outbox, and bitemporal integrity boundary.
- No foreign CWL repository is mutated and no cross-service application-table SQL is introduced.

## Standards rationale

NIST SP 800-53 Rev. 5 / current control catalog 5.1 describes least privilege (AC-6) and audit-record content (AU-3). The design applies least privilege by authorizing before protected vacancy resolution and preserves the existing auditable authoritative Assignment mutation instead of creating a parallel staffing store.
