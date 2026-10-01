# ADR 0010: Naruon calendar integration uses a fail-closed intent adapter

## Status

Accepted on protected `develop`.

## Context

Orgmetra needs to turn authorized HR workflow milestones into useful calendar actions without owning calendar-provider credentials, copying Naruon, or directly querying another service's application database. Naruon protected `develop` at `ddd05c5aaf3e170aa2bdc4412647b43b95d5a6b9` publishes `POST /api/calendar/writeback-intent` with customer-owned CalDAV source selection, intent provenance, and an optional provider-execution flag.

The same Naruon revision currently rejects provider execution for a `create` intent because execution requires a non-null `if_match` even though `create` correctly has no If-Match precondition. Exact reproduction and owner-side acceptance criteria were routed to the existing Naruon owner issue `ContextualWisdomLab/naruon#1350`; Orgmetra must not patch or locally duplicate that foreign execution boundary.

## Decision

Orgmetra introduces a transport-neutral `orgmetra-naruon-adapter` package that consumes only Naruon's published API contract.

- Orgmetra requires an opaque tenant identifier, exact HR resource reference, actor reference, purpose, reason, evidence version, and explicit human confirmation before it can build a calendar intent.
- Buyer-facing summaries are selected from a fixed purpose-specific vocabulary and contain no person name, tenant identifier, HR record identifier, actor reference, free-form evidence, or credential.
- The adapter requests `action=create` with `execute_provider=false`. It therefore creates an inspectable intent and never mutates a customer calendar provider in this slice.
- Authentication and HTTP transport remain host responsibilities; the adapter never accepts or stores credentials.
- Naruon responses are fail-closed: unknown/missing fields, wrong target source, non-CalDAV protocol, non-customer-owned writeback mode, If-Match on create, unexpected provider execution, execution metadata, or provenance drift are rejected.
- The returned Orgmetra audit context remains separate from the Naruon request body so the owning host can append governed audit/outbox evidence without leaking HR identifiers into calendar summary text.
- Provider-executed create remains deliberately out of scope until the Naruon owner repair integrates and Orgmetra revalidates the exact published contract. No Orgmetra workaround may bypass that owner boundary.

## Consequences

Orgmetra can safely prepare and validate buyer-visible calendar intents while preserving standalone operation, tenant/purpose evidence, human confirmation, PII minimization, and service ownership. The cost is that a user cannot complete provider writeback through this adapter until the Naruon execution defect is repaired and revalidated; the product must present that state as an intent awaiting an executable provider path rather than claiming calendar mutation succeeded.

## Verification

The owning package requires exact 100% statement and branch coverage. Regressions cover malformed identities and resource references, missing human confirmation, unsupported action kinds, PII-free request bodies, target-source matching, contract-key drift, provenance drift, unexpected provider execution, and intent-only execution metadata. The exact-head quality workflow checks out the candidate SHA, uses the repository's reviewed hashed Python test toolchain, compiles the package, runs branch coverage, and requires a clean checkout.

## Standards and evidence

The adapter does not implement CalDAV or iCalendar itself; Naruon owns that provider boundary. The protocol semantics that constrain the owner contract are recorded in `docs/doctoring/naruon-calendar-intent-references.md` together with the exact Naruon contract revision used by this ADR.
