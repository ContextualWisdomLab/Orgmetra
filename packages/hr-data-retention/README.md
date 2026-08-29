# Orgmetra HR Data Retention Review

This package creates **review evidence**, not deletion authority. It helps an authorized HR/privacy operator answer the next safe question when a governed retention date is reached or a legal hold applies: *what must be re-resolved before any disposition can even be considered?*

## What the packet binds

`HrDataRetentionReviewPacket` records only governance metadata and opaque references:

- the authoritative Orgmetra tenant and target resource reference;
- one reviewed record-category code;
- the retention-policy reference and exact SHA-256 digest reviewed by the human;
- the reviewed retention due date;
- a closed legal-hold state, with immutable hold evidence when the state is active;
- distinct requester and reviewer actor references;
- evidence version and exact UTC system-recorded time.

The packet deliberately carries no employee/candidate name, email, salary, assessment score, free-form HR content, or copied policy text. `repr(...)` is redacted. The packet is runtime-final, so callers cannot subclass it to replace derived governance properties such as `disposition_authorization_state` with forged authority before canonical serialization.

Construction also seals the exact canonical evidence digest in a process-local identity-keyed weak registry outside packet-writable state. Canonicalization first revalidates the live fields and then verifies that the well-formed current evidence still matches that creation-time seal. This means low-level replacement of a policy digest, reviewer, reviewed date, or coherent legal-hold evidence is rejected rather than silently becoming a second audit fact; a forged in-object seal is not available. Value copies and pickle restoration rebuild through the governed constructor and receive independent seals. A legitimate correction must create a new governed packet/evidence version and flow through the durable append-only audit boundary; it does not rewrite an already-issued in-memory review artifact.

## Fail-closed disposition states

The packet never returns an authorization to delete data.

- An active legal hold produces `retain_legal_hold`.
- A review on or before the policy due date produces `retain_until_due`.
- A review after the due date produces only `requires_authoritative_disposition_review`.

All three states retain `disposition_authorization_state=not_authorized_to_delete` and `scope_verification_state=requires_authoritative_resolution`.

Before any later disposition executor acts, the host must independently re-resolve the current tenant/resource binding, applicable retention policy, jurisdiction and record category, legal-hold state, reviewer authority, and immutable audit evidence. A passed date is therefore a **review trigger**, never proof that deletion is lawful or safe.

## Why the policy duration is not hard-coded here

Employment-record retention periods differ by record class, jurisdiction, employer type, legal hold, litigation/charge status, and other obligations. For example, current EEOC guidance describes one-year retention for many private-employer personnel/employment records, longer periods for some other covered entities and record types, and preservation through final disposition when a discrimination charge or action applies. Orgmetra therefore binds the exact authoritative policy evidence reviewed by the human instead of embedding one universal statutory duration in application code.

## Verification

Run the package quality contract with:

```bash
PYTHONPATH=packages/hr-data-retention/src \
  python -m pytest -c packages/hr-data-retention/pyproject.toml \
  packages/hr-data-retention/tests
```

Owned production statement and branch coverage are both required to remain exactly 100%.
