# ADR 0142: Purpose-bound employee assignment-history read

- **Status:** Accepted on active PR #142; not protected-main truth until integrated.
- **Date:** 2026-08-28
- **Owners:** Orgmetra People API / HRIS core
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization)

## Decision

The employee profile reads assignment history through a read-only People API boundary that authorizes the exact tenant, person, purpose, operation, and requested field set **before** calling the persistence adapter. The persistence adapter remains injected; this slice does not introduce direct SQL or a second Assignment source of truth.

Each returned row carries separate business-effective (`effective_from`, `effective_to`) and system-recorded (`recorded_from`, `recorded_to`) coordinates. `known_at` selects the half-open recorded interval `[recorded_from, recorded_to)`. Trust-bearing system instants require an exact built-in `datetime` paired with Python's built-in fixed-offset `timezone` at zero offset; caller-defined `tzinfo` providers are rejected before protected retrieval or row use so validation, comparison, and canonical rendering cannot depend on mutable user-supplied timezone behavior. Orgmetra then revalidates tenant/person scope, recorded-time visibility, row type, and assignment identity uniqueness because persistence output is untrusted at the service boundary.

Only fields granted by the purpose-bound authorization decision are emitted. Assignment identity is **not** an unconditional envelope field: a caller that is authorized only for `effective_from` receives only `effective_from`. This prevents a row identifier from becoming an accidental side channel around field minimization.

Results are deterministically ordered by business-effective start and assignment UUID. Allocation values use an exact four-decimal `Decimal` representation in `(0, 1.0000]`; the read path does not infer FTE semantics beyond the authoritative Assignment fact.

## Security and privacy consequences

This boundary follows resource-centric, per-request authorization. NIST SP 800-207 describes authorization before establishing access to an enterprise resource, while SP 800-207A extends identity-based granular policy enforcement to application and service boundaries. The implementation therefore delegates policy evaluation to Orgmetra's existing Keyverse adapter contract rather than embedding a second authorization engine.

The response intentionally excludes display name, contact data, compensation, ratings, assessments, candidate data, credentials, prompts, and model output. A caller may request only explicitly supported assignment-history fields, and schema drift fails closed.

## Data consequences

This ADR does not change the normalized Job / Position / Employment / Assignment model. It exposes historical Assignment versions for one authorized person while preserving the distinction between business time and system-recorded time required by ADR 0003. A future PostgreSQL adapter must remain tenant-scoped/RLS-governed and must not bypass the People service with cross-service application-table SQL.

## Verification

PR #142 must demonstrate:

1. denied fields cause zero persistence calls;
2. tenant/person or system-time mismatches fail closed;
3. caller-defined UTC-looking timezone providers fail closed before protected retrieval or persisted row use;
4. duplicate visible assignment identities fail closed;
5. only authorized fields are returned;
6. canonical allocation/time representations and deterministic ordering;
7. exact 100% owned People API statement and branch coverage on the current PR head;
8. applicable Foundation, SAST, Security, Recovery, and central required-workflow evidence before any integration decision.
