# ADR-0006: Dependency-injected scope-and-purpose-bound People API

- Status: Proposed on active PR
- Date: 2026-08-15
- Updated: 2026-08-16
- Owners: Orgmetra maintainers
- Depends on: ADR-0005
- Supersedes: none

## Context

The People API is a high-trust HR boundary. Tenant, actor, OAuth capability,
business purpose, system-recorded time, and decision provenance must not be
caller-selected merely because a request can carry a header or JSON field.
Internal trace identifiers must also remain operator-only rather than becoming a
client correlation handle.

## Decision

Orgmetra provides an independently importable FastAPI application factory with
these contracts:

1. the host injects `TokenAuthorizer` and `PeopleRepository`; there is no static
   production token, environment bypass, caller tenant header, or permissive CORS
   fallback;
2. every protected route selects both an operation scope and a finer HR business
   purpose in server code; the authorizer and API defensively require both;
3. the authorizer returns opaque tenant and actor references plus independently
   granted scopes and purposes;
4. the API constructs `PurposeContext`; callers cannot select tenant, actor,
   purpose, decision reference, or evidence reference;
5. `X-Correlation-Id` is the only optional workflow metadata header in this slice;
6. person commands accept effective/business time but not system-recorded time;
   persistence owns `recorded_from` using the database clock;
7. synchronous repository calls execute through Starlette's threadpool boundary;
8. declared and observed request bytes are bounded;
9. explicit and framework HTTP failures use RFC 9457-compatible non-leaking
   problem documents with a random `err_...` support reference and actionable
   `next_action`;
10. internal trace references never appear in response headers or problem bodies;
11. Swagger and ReDoc UI remain disabled in the pre-GA service;
12. People API route modules keep runtime annotations and `Depends` defaults so
    FastAPI cannot treat `PurposeContext`, `Request`, or the repository port as
    caller query fields. `from __future__ import annotations` is forbidden in
    `app.py` because postponed annotations made those server-owned objects look
    like request input under FastAPI 0.116.

## Alternatives considered

### Purpose-only authorization

Rejected. Business purpose answers why an actor may use data; OAuth-style scope
answers which API capability the token carries. Either dimension alone can
accidentally enlarge authority.

### Caller-provided decision/evidence headers

Rejected as audit authority. Opaque-looking references can still be fabricated,
cross-tenant, stale, or point at unsealed evidence. High-impact workflows must
resolve governed versioned evidence inside an authorized application boundary.

### Caller-provided recorded time

Rejected. A client may state effective/business time, but knowledge/system time
must be assigned by the authoritative persistence boundary so backdating or
future-dating cannot rewrite what the system knew when.

### Client-visible internal trace IDs

Rejected. A separate cryptographically random support reference gives customers a
handle for support without disclosing tracing topology or embedding tenant,
actor, timestamp, or decision semantics.

## Consequences

- Keyverse and other identity adapters must implement the two-dimensional
  scope-plus-purpose authorizer contract before this stack can retarget.
- The persistence slice must provide an atomic idempotency ledger and governed
  high-impact decision/evidence contract before mutation endpoints are GA-ready.
- Ingress request-size limits, readiness, rate limiting, telemetry, deployment,
  SBOM/provenance, recovery evidence, and external security/privacy review remain
  release gates.

## Failure and recovery

Authentication and authorization failures deny access before repository
invocation. Malformed correlation metadata and body overflows fail before a
mutation. Repository conflict, access denial, and outage map to fixed 409, 403,
and 503 responses. Unexpected failures return fixed text plus only the
client-safe support reference.

## Verification

- negative tests proving purpose cannot substitute for scope and scope cannot
  substitute for purpose;
- server-selected tenant/actor/purpose context tests;
- caller decision/evidence headers cannot become repository audit provenance;
- caller `recorded_at` is rejected and excluded from the repository port;
- declared and observed request-byte probes;
- random support-reference shape plus no internal trace disclosure;
- RFC 9457 problem shape, safe framework-error normalization, and non-echo tests;
- exact 100% production statement/branch coverage and public docstring gates on
  supported Python lanes once the stack can obtain fresh hosted evidence.

## Security and governance impact

Identity, capability, purpose, tenant, persistence time, and decision evidence
are separate reviewable authorities. This supports least privilege and audit
evidence readiness for CSAP/SOC 2-oriented engineering without claiming
certification.
