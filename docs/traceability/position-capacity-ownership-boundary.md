# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding and the `<= 1.0000` visible seat-allocation invariant.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, People-owned terminal `AssignmentAttemptOutcome`, the published/versioned cross-context capacity/attempt API or event contract, writer-fenced migration, two-service reconciliation, performance evidence, or rollback rehearsal.

## Requirement matrix

| Requirement | Current evidence | State |
|---|---|---|
| Keep Position in Organization and Assignment in People | `ARCHITECTURE.md`, `docs/TRD.md` | protected_architecture |
| Preserve durable Position identity/bitemporal versions and Assignment binding | ADR 0004 | protected_accepted |
| Preserve `active|open` Position coverage and visible seat allocation `<= 1.0000` | ADR 0005 | protected_accepted |
| Record why synchronous availability-check-only is unsafe | PostgreSQL 18 §13.2 plus ADR 0274 alternative B | proposed_design |
| Define one canonical capacity authority without cross-service SQL | ADR 0274 option C | proposed_design |
| Make `held` consume capacity but allow bounded autonomous expiry before commit fence | ADR 0274 capacity invariant/protocol | proposed_design |
| Make `commit_fenced` consume capacity without autonomous expiry | ADR 0274 protocol/failure semantics | proposed_design |
| Bind every fenced Assignment operation to one opaque `assignment_attempt_id` | ADR 0274 domain model/protocol | proposed_design |
| Make People commit Assignment and terminal `committed` attempt evidence atomically | ADR 0274 `create_assignment` protocol | proposed_design |
| Allow post-fence capacity release only from a terminal People `aborted` tombstone that fences later commit | ADR 0274 `terminalize_attempt`/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Bind retries to idempotency key plus semantic command digest | ADR 0274 protocol | proposed_design |
| Keep Person/Employment payload and unrelated PII out of Organization capacity evidence | ADR 0274 domain model | proposed_design |
| Prevent dual Position/capacity writers during extraction | ADR 0274 cutover/rollback | proposed_design |
| Preserve current People mutation behavior while prerequisites remain mutable | #64 owner path; no extraction source in this slice | active_owner_boundary |
| Preserve Organization hierarchy prerequisite delta before extraction | #96 -> #119 owner order | active_owner_boundary |
| Prove concurrent overlapping capacity cannot exceed `1.0000` | Future two-service/PostgreSQL acceptance | planned_red_green |
| Prove delayed create versus terminal abort cannot produce both an aborted receipt and later committed Assignment | Future People attempt-race acceptance | planned_red_green |
| Prove crash after People commit before confirm cannot free capacity | Future forced-crash interleaving | planned_red_green |
| Prove exact replay and same-key/different-digest rejection | Future contract/integration tests | planned_red_green |
| Prove stale Position version, correction/end, reconciliation, and out-of-order delivery | Future contract/integration tests | planned_red_green |
| Prove migration projection equivalence and single-writer rollback | Future migration/recovery rehearsal | planned_red_green |
| Prove reserve/fence/create/terminalize/confirm/release buyer path p95 <= 20 ms under real concurrency | Future k6/E2E measurement | planned_performance |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## State-machine acceptance

The implementation must exercise, not merely document, these transitions and forbidden transitions:

| Starting state | Event/evidence | Required result |
|---|---|---|
| none | capacity-valid `reserve` | `held` and capacity debit bound to one `assignment_attempt_id` |
| `held` | bounded expiry before fence | `expired`; capacity returned |
| `held` | exact `arm_commit_fence` | `commit_fenced`; capacity remains consumed and loses autonomous expiry |
| People attempt unresolved | `create_assignment` wins attempt serialization | Assignment and terminal `committed` outcome in one People transaction |
| People attempt unresolved | `terminalize_attempt` wins attempt serialization | terminal `aborted` tombstone; every later create for that attempt is fenced |
| People attempt `aborted` | delayed/retried `create_assignment` | no Assignment commit; replay/fail closed as aborted |
| People attempt `committed` | delayed/retried `terminalize_attempt` | return committed; no abort tombstone and no Organization release authority |
| `commit_fenced` | terminal People `committed` receipt for exact attempt/version/digest | `confirmed` idempotently |
| `commit_fenced` | terminal People `aborted` receipt for exact attempt/version/digest | `released` idempotently |
| `commit_fenced` | current Assignment absence / not-found / timeout / missing event / stale read | no release; reconciliation only |
| `confirmed` | duplicate confirm with same version/digest | same confirmed result |
| any live debit | same idempotency key with different semantic digest | fail closed |

The Organization aggregate capacity calculation counts every effective `held`, `commit_fenced`, and `confirmed` debit. The People attempt outcome is independently monotonic and terminal. Together these rules prevent two concurrent holds from both exceeding capacity, prevent a committed-but-unconfirmed Assignment from reopening capacity, and prevent a delayed create from committing after Organization released a fenced debit on an abort receipt.

## Required failure interleaving

A specific regression must preserve the causal counterexample that tightened ADR 0274:

1. Organization creates and commit-fences reservation R for attempt A.
2. People `create_assignment(A, R)` is delayed or in flight and no Assignment is yet visible.
3. Reconciliation attempts to resolve A.
4. A mere authoritative read returning no Assignment must **not** authorize release.
5. If `terminalize_attempt(A)` records `aborted`, the delayed create must be unable to commit afterward.
6. If the delayed create commits first, it must atomically record terminal `committed`; terminalization must return that committed outcome and Organization must not release R.

Passing this regression requires exactly one terminal People outcome for A and no interleaving that frees Organization capacity while a later commit for A remains possible.

## Extraction gate

Do not start Position source/schema extraction from this branch. The causal order is:

`#64 protected integration -> #96 protected integration -> #119 non-force protected adoption/integration -> ADR 0274 executable RED/GREEN owner stack -> writer-fenced migration -> normal protected integration`

If executable evidence invalidates the provisional commit-fence design, revise ADR 0274 while it is still Proposed and compare the two-phase `pending_capacity` Assignment alternative. Do not preserve a weak design merely to keep the document stable.

## Evidence boundary

Passing documentation checks would prove only that the Proposed decision record is internally present. It would not prove service extraction, concurrency safety, availability, performance, security, or commercial readiness. Historical #64/#96 checks do not transfer to a future extraction head; every implementation candidate must obtain fresh exact-head evidence.
