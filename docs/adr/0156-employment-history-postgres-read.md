# ADR 0156: Read Employment history from canonical PostgreSQL truth

- **Status:** Proposed on active stacked PR #156; not protected-`develop` truth until integrated
- **Date:** 2026-08-30
- **Owners:** Orgmetra People API / HRIS persistence
- **Extends:** ADR 0003 (bitemporal HRIS data), ADR 0008 (purpose-bound PII authorization), ADR 0149 (Employment-history read contract), ADR 0155 (Employment-history HTTP read)

## Context

PR #155 exposes the customer-callable Employment-history HTTP boundary but keeps persistence injected. An integrated deployment still needs one canonical adapter for normalized `employment_record` and `employment_record_version` truth; otherwise each host could supply persistence code with different tenant or system-time semantics.

The adapter is not an authorization engine or a second source of truth. The parent People service authorizes before calling it and revalidates its typed output before disclosure. The existing schema owns Employment identity, Person binding, bitemporal version facts, tenant RLS, and immutable-history guards.

The retired feature-local PostgreSQL workflow did not start PostgreSQL or execute this adapter against the schema; its name therefore cannot be used as real-database evidence. Repository-owned PostgreSQL acceptance belongs to canonical Foundation CI.

Fresh comparison with canonical governed-People persistence exposed two retained-authority risks. First, a frozen/slotted dataclass still retained its validated `connection_factory` in a writable slot that `object.__setattr__` can replace after construction. Second, exact outer `uuid.UUID` type did not prove its retained `.int` payload was an exact built-in integer, and the caller-owned UUID object remained live across connection acquisition. Employment-history persistence therefore must structurally bind the exact accepted executable capability and detach exact validated UUID scalar authority before invoking any external database capability.

## Decision

Add `PostgresEmploymentHistoryReadPort` as the PostgreSQL implementation of the `EmploymentHistoryReadPort` protocol.

The adapter:

1. validates and structurally binds the exact callable connection capability in immutable tuple payload, then invokes that stored capability directly rather than performing a later replaceable attribute lookup;
2. validates exact tenant/Person UUID wrappers, reads each retained `.int` once, requires exact built-in integer authority in the operational UUID range before any equality/range behavior, reconstructs fresh UUID values from those detached scalars, and never passes caller-owned UUID aliases into the database capability;
3. validates an exact built-in UTC `known_at` before acquiring a connection;
4. opens one `READ COMMITTED, READ ONLY` transaction and sets the transaction-local tenant context before the protected query;
5. joins only Orgmetra-owned `employment_record_version` to its `employment_record` anchor, preserving Person scope without joining another bounded context's application tables;
6. applies explicit tenant, Person, parent-recorded, and version-recorded half-open predicates;
7. projects recorded timestamps with `AT TIME ZONE 'UTC'`, accepts only exact naive UTC DB projections, and attaches built-in UTC after validation; and
8. treats DB-API output as untrusted by checking the default list collection, exact tuple row shape, domain reconstruction, requested target identity, and knowledge-cutoff visibility before returning an immutable tuple.

Purpose-bound field authorization remains in the parent service. This adapter performs no mutation, audit/outbox write, foreign-service call, disclosure, or high-impact employment decision.

Real PostgreSQL acceptance extends the already canonical `tests/test_bitemporal_postgres.sh` contract instead of introducing another feature-local workflow or an untracked PostgreSQL script. The contract parses the adapter source, extracts `_READ_ONLY_SQL`, `_TENANT_CONTEXT_SQL`, and `_EMPLOYMENT_HISTORY_SQL`, requires their placeholder shape, substitutes only psql-bound values, and executes those exact statements against the seeded canonical schema. This keeps the database contract coupled to the production SQL while leaving Python DB-API shape/error, retained-input, and executable-capability behavior in the People unit suite.

## Consequences

### Positive

- The Employment-history application contract can use canonical normalized PostgreSQL truth without host-specific persistence code.
- The executable database dependency accepted at construction cannot be replaced through a later instance-slot mutation before the protected read.
- A forged exact UUID wrapper cannot make a caller-defined retained payload executable during validation, and a caller-owned UUID alias cannot retarget tenant/Person query parameters after validation.
- Read-only transaction mode, explicit predicates, and tenant context provide layered database scope controls.
- Person, Employment identity, and Employment-version history remain separate while business-effective time stays distinct from system-recorded visibility.
- Exact DB timestamp validation prevents driver/session timezone behavior from changing evidence meaning.
- The real-database contract checks pre/post-correction system-time reconstruction, the exact half-open recorded boundary, foreign-tenant target exclusion, session-TimeZone-independent UTC projection, and read-only write rejection using the production SQL constants rather than a handwritten query copy.

### Trade-offs

- The adapter is PostgreSQL/DB-API specific and intentionally requires the default tuple-row contract.
- The source-exact shell contract exercises PostgreSQL semantics through `psql`; the Python unit suite remains responsible for connection-factory, cursor, row-shape, domain-reconstruction, retained-input, and capability-binding behavior. Neither alone substitutes for the other.
- Structural binding and scalar detachment protect supported boundaries; they are not a claim of isolation from arbitrary code already executing inside the trusted service interpreter.
- Explicit query predicates are defense in depth, not RLS evidence. The existing tenant-isolation PostgreSQL contract remains the authority for forced-RLS behavior under non-bypass application roles.
- The parent service must continue to revalidate rows before serialization.

## Verification

The contract-first child test head `1a8b9fb7` failed during collection while the adapter module was absent. Capability regression `5a8c95f5942824d712a80ee4261ec320596605ad` then required `object.__setattr__` replacement of the validated factory to fail and the originally accepted factory to remain the one executed; its parent implementation still stored the dependency in the frozen dataclass slot. Production repair `a41ef5278ef45b15c1ab721244c40b35f828907a` replaces that slot-backed storage with immutable tuple payload and direct tuple access.

A second test-first head `16dddcea47c60ceb0e2abc5154ffad5f03c484a2` proves two distinct retained-input failures: a forged exact UUID whose `.int` payload has executable equality must fail before database access, and a connection factory that mutates caller-owned UUID aliases after validation must not change the tenant context or SELECT parameters. Production repair `0d0993b3a9541cef4ddc7050df47ee55fc318a59` validates the retained payload as exact built-in `int`, detaches it to scalar authority, reconstructs fresh UUIDs before connection acquisition, and uses only those detached identities for PostgreSQL parameters and post-read target checks.

Source-equivalent causal execution reproduces the predecessor forged-payload failure and the repaired fail-closed behavior, but this is not hosted PR evidence. Current source also contains the canonical Foundation-owned real PostgreSQL contract in `tests/test_bitemporal_postgres.sh`, which seeds isolated Employment history, executes the exact adapter SQL at two knowledge cutoffs and the closing/opening boundary under non-UTC session time zones, confirms a foreign-tenant Person target yields no row, and proves the adapter's exact read-only transaction statement rejects writes.

No hosted GREEN is claimed on the current stacked head: canonical Foundation's pull-request trigger targets `develop`, while #156 intentionally targets #155. Parent or predecessor runs do not transfer. After the owner stack reaches protected `develop`, #156 must ordinary-forward onto that truth, retarget to `develop`, and reacquire the exact-head Foundation PostgreSQL execution, full People statement/branch coverage, security checks, model review, and qualifying independent approval before this ADR can advance from Proposed.

The implementation follows PostgreSQL transaction access-mode guidance and the existing protected Orgmetra RLS contract. These controls are defense in depth and do not authorize merge, release, or protected-branch representation while the required exact-head evidence is absent.
