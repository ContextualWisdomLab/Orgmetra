# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding, `active` or `open` Position coverage, and the `<= 1.0000` visible seat-allocation invariant.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity/status coverage in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity/eligibility ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, `PositionEligibilityCoverage`, People-owned terminal `AssignmentAttemptOutcome`, the published/versioned cross-context capacity/attempt API or event contract, Position-eligibility fencing, transaction-drained writer-fenced migration, deterministic discrepancy manifest, two-service reconciliation, performance evidence, or rollback rehearsal.

## Requirement matrix

| Requirement | Current evidence | State |
|---|---|---|
| Keep Position in Organization and Assignment in People | `ARCHITECTURE.md`, `docs/TRD.md` | protected_architecture |
| Preserve durable Position identity/bitemporal versions and Assignment binding | ADR 0004 | protected_accepted |
| Preserve `active` or `open` Position coverage and visible seat allocation `<= 1.0000` | ADR 0005 | protected_accepted |
| Preserve union coverage when one Assignment interval spans multiple staffable Position versions | protected `validate_assignment_position_coverage` plus ADR 0274 `PositionEligibilityCoverage` | proposed_design |
| Record why synchronous availability/status-check-only is unsafe | PostgreSQL 18 §13.2 plus ADR 0274 alternative B | proposed_design |
| Define one canonical capacity/eligibility authority without cross-service SQL | ADR 0274 option C | proposed_design |
| Make `held` consume capacity but allow bounded autonomous expiry before commit fence | ADR 0274 capacity invariant/protocol | proposed_design |
| Make `commit_fenced` consume capacity without autonomous expiry | ADR 0274 protocol/failure semantics | proposed_design |
| Bind every fenced Assignment operation to one opaque `assignment_attempt_id` | ADR 0274 domain model/protocol | proposed_design |
| Make People commit Assignment and terminal `committed` attempt evidence atomically | ADR 0274 `create_assignment` protocol | proposed_design |
| Allow post-fence capacity release only from a terminal People `aborted` tombstone that fences later commit | ADR 0274 `terminalize_attempt`/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Bind `arm_commit_fence` to normalized complete Position eligibility coverage for the reservation interval | ADR 0274 capacity/eligibility invariant | proposed_design |
| Serialize eligibility-changing Position mutations against live fenced/confirmed reservations at the same Position root | ADR 0274 `change_position_status_or_version` protocol | proposed_design |
| Reject People-side mutable Position recheck as a correctness mechanism after a fence | ADR 0274 protocol/failure semantics | proposed_design |
| Keep People/network I/O outside Position-root transactions and row-lock lifetime | ADR 0274 protocol/failure semantics | proposed_design |
| Apply terminal People receipts in a new local Organization transaction rather than waiting under a Position lock | ADR 0274 confirm/release protocol | proposed_design |
| Fail conflicting Position changes locally, resolve People state outside the lock, then retry on exact version/digest evidence | ADR 0274 status-change protocol | proposed_design |
| Bind retries to idempotency key plus semantic command digest | ADR 0274 protocol | proposed_design |
| Keep Person/Employment payload and unrelated PII out of Organization capacity evidence | ADR 0274 domain model | proposed_design |
| Prevent dual Position/capacity writers during extraction | ADR 0274 cutover/rollback | proposed_design |
| Drain every pre-fence legacy mutation before taking the migration snapshot | ADR 0274 cutover barrier | proposed_design |
| Deterministically map each tenant-qualified legacy Assignment to confirmed reservation/terminal committed migration evidence | ADR 0274 cutover manifest | proposed_design |
| Fail cutover instead of rewriting an invalid/unrepresentable legacy fact to fit the target ledger | ADR 0274 cutover discrepancy rule | proposed_design |
| Preserve current People mutation behavior while prerequisites remain mutable | #64 owner path; no extraction source in this slice | active_owner_boundary |
| Preserve Organization hierarchy prerequisite delta before extraction | #96 -> #119 owner order | active_owner_boundary |
| Prove concurrent overlapping capacity cannot exceed `1.0000` | Future two-service/PostgreSQL acceptance | planned_red_green |
| Prove delayed create versus terminal abort cannot produce both an aborted receipt and later committed Assignment | Future People attempt-race acceptance | planned_red_green |
| Prove Position close/status mutation cannot invalidate eligibility while an authentic fenced create can still commit | Future Position-status-vs-create race acceptance | planned_red_green |
| Prove a multi-version staffable Position coverage set remains complete and fenced across version boundaries | Future Position-coverage acceptance | planned_red_green |
| Prove remote latency cannot extend Position row-lock lifetime | Future lock/I/O instrumentation acceptance | planned_operability |
| Prove crash during external status-change coordination leaves the original Position/fence authoritative and recoverable | Future coordination crash acceptance | planned_red_green |
| Prove crash after People commit before confirm cannot free capacity or eligibility | Future forced-crash interleaving | planned_red_green |
| Prove exact replay and same-key/different-digest rejection | Future contract/integration tests | planned_red_green |
| Prove correction/end, reconciliation, and out-of-order delivery | Future contract/integration tests | planned_red_green |
| Prove a pre-fence legacy transaction cannot commit after projection starts | Future cutover-barrier concurrency test | planned_recovery |
| Prove deterministic migration identity/digest replay and complete projection equivalence | Future migration/recovery rehearsal | planned_recovery |
| Prove invalid legacy occupancy creates deterministic discrepancy evidence and no authority switch | Future migration failure rehearsal | planned_recovery |
| Prove migration projection equivalence and single-writer rollback | Future migration/recovery rehearsal | planned_red_green |
| Prove reserve/fence/create/terminalize/confirm/release and conflicting Position-change buyer paths at p95 <= 20 ms under real concurrency | Future k6/E2E measurement | planned_performance |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## State-machine acceptance

The implementation must exercise, not merely document, these transitions and forbidden transitions:

| Starting state | Event/evidence | Required result |
|---|---|---|
| none | capacity-valid, Position-eligible `reserve` | `held` and capacity debit bound to one `assignment_attempt_id` |
| `held` | bounded expiry before fence | `expired`; capacity returned |
| `held` | exact `arm_commit_fence` with complete staffable Position interval coverage | `commit_fenced`; capacity and Position eligibility remain reserved and autonomous expiry stops |
| People attempt unresolved | `create_assignment` wins attempt serialization | Assignment and terminal `committed` outcome in one People transaction |
| People attempt unresolved | `terminalize_attempt` wins attempt serialization | terminal `aborted` tombstone; every later create for that attempt is fenced |
| People attempt `aborted` | delayed/retried `create_assignment` | no Assignment commit; replay/fail closed as aborted |
| People attempt `committed` | delayed/retried `terminalize_attempt` | return committed; no abort tombstone and no Organization release authority |
| `commit_fenced` | terminal People `committed` receipt already obtained outside the Position lock | local Organization `confirmed` transition, idempotently |
| `commit_fenced` | terminal People `aborted` receipt already obtained outside the Position lock | local Organization `released` transition, idempotently |
| `commit_fenced` | current Assignment absence / not-found / timeout / missing event / stale read | no release; reconciliation only |
| Position has effective `commit_fenced` or `confirmed` debit | proposed status/version mutation removes staffable coverage from any covered debit slice | local transaction fails closed with conflict; no People/network call while the Position lock is held |
| status-change conflict recorded | governed external coordination resolves People attempt/Assignment and durable receipts | apply receipts in separate Organization transactions, then retry exact status/version command against current version/digest |
| `confirmed` | duplicate confirm with same version/digest | same confirmed result |
| any live debit | same idempotency key with different semantic digest | fail closed |
| legacy writer open | cutover fence enters draining epoch | no new legacy admission; snapshot waits for every pre-fence admitted transaction to commit/rollback |
| cutover barrier closed | deterministic migration projection | every visible current/future legacy Assignment maps to stable `confirmed` reservation plus terminal committed migration evidence and reproducible eligibility-coverage digest |
| drained legacy snapshot invalid or unrepresentable | migration validation | immutable deterministic discrepancy evidence; no source fact is silently rewritten and authority does not switch |

The Organization aggregate capacity calculation counts every effective `held`, `commit_fenced`, and `confirmed` debit. The same Position-root authority also protects staffable eligibility for every `commit_fenced`/`confirmed` interval against incompatible status/version mutation. The People attempt outcome is independently monotonic and terminal. Cross-context calls happen only after local row-locking transactions have ended. Together these rules prevent two concurrent holds from exceeding capacity, prevent a committed-but-unconfirmed Assignment from reopening capacity, prevent a delayed create from committing after an abort receipt, prevent an authentic fence from becoming semantically stale because Organization independently closed the Position, and avoid turning a PostgreSQL row lock into a distributed network lock.

## Required failure interleavings

### Delayed create versus terminal abort

1. Organization creates and commit-fences reservation R for attempt A.
2. The Organization transaction ends and releases its Position row lock.
3. People `create_assignment(A, R)` is delayed or in flight and no Assignment is yet visible.
4. Reconciliation attempts to resolve A.
5. A mere authoritative read returning no Assignment must **not** authorize release.
6. If `terminalize_attempt(A)` records `aborted`, the delayed create must be unable to commit afterward.
7. If the delayed create commits first, it must atomically record terminal `committed`; terminalization must return that committed outcome and Organization must not release R.

Passing requires exactly one terminal People outcome for A and no interleaving that frees Organization capacity while a later commit for A remains possible.

### Fenced create versus Position eligibility change

1. The reservation interval has complete `active`/`open` coverage. That coverage may be one Position version or a normalized union of several contiguous visible Position versions. Organization commit-fences reservation R with the exact coverage digest, then commits and releases its Position lock.
2. People `create_assignment(A, R)` is delayed before commit.
3. A concurrent Organization command proposes a version change that would make part of R's covered interval `closed` or otherwise Assignment-ineligible.
4. Organization serializes that mutation against R at the Position root and fails the local transaction closed with durable conflict evidence. It does **not** call People while holding the Position lock.
5. A separate governed workflow, outside any Position transaction, terminalizes/corrects the affected People attempt/Assignment as necessary. Durable People receipts are then applied by new idempotent Organization transactions.
6. Only after the incompatible live debit/Assignment has been resolved may the exact Position mutation be retried against the current Position/reservation version.
7. If the external workflow crashes at any point, the prior eligible coverage plus the existing reservation fence remain authoritative; recovery resumes idempotently rather than leaving a half-held distributed lock.
8. People must not rely on a `GET current Position status` check immediately before its Assignment write, because the same check-then-write race would remain.

Passing requires that no execution exposes a durable Assignment outside the staffable Position coverage promised by its authentic fenced receipt and that no remote latency extends the local Position row-lock lifetime.

### Legacy cutover versus in-flight mutation

1. Start a legacy People Position/Assignment capacity mutation and keep its database transaction open after admission but before commit.
2. Start cutover and atomically move the durable admission gate to the draining/fenced epoch.
3. A later legacy mutation must be rejected from admission.
4. Migration snapshot/projection must remain blocked while the pre-fence transaction is unresolved.
5. Commit or roll back that pre-fence transaction. Only then may the cutover barrier close and record its authoritative knowledge timestamp/high-water evidence.
6. Take the migration snapshot and project it twice. Both projections must produce identical tenant-qualified migration attempt/reservation identities, `confirmed` states, terminal committed evidence, normalized Position-eligibility coverage digests, and manifest digest.
7. No transaction admitted under the legacy epoch may commit after that snapshot or after Organization authority is enabled.

Passing requires an explicit linearization barrier rather than a timing heuristic, plus deterministic replay of the complete migration projection.

### Invalid legacy occupancy versus authority switch

1. Close the cutover barrier only after all pre-fence legacy transactions are terminal.
2. Use a deterministic fixture/snapshot containing a source fact that cannot be represented without changing its meaning: for example aggregate overlapping allocation above `1.0000`, an Assignment interval without complete staffable Position coverage, or an ambiguous tenant-qualified identity.
3. Run the complete projection/validation twice.
4. Both runs must produce identical discrepancy identity/digest and identify the exact source fact/invariant conflict without creating a replacement truth.
5. The migration must not drop, clamp, split, round, synthesize, or silently rewrite the source Assignment/Position evidence to make the target ledger valid.
6. Organization authority must remain disabled and the cutover must stay fenced until governed correction is committed under the still-authoritative legacy owner and the full snapshot/projection is rerun.

Passing requires migration failure to be deterministic, auditable, and lossless with respect to the source truth; target validity cannot be manufactured by semantic normalization.

## Extraction gate

Do not start Position source/schema extraction from this branch. The causal order is:

`#64 protected integration -> #96 protected integration -> #119 non-force protected adoption/integration -> ADR 0274 executable RED/GREEN owner stack -> transaction-drained writer-fenced migration -> normal protected integration`

If executable evidence invalidates the provisional commit-fence design, revise ADR 0274 while it is still Proposed and compare the two-phase `pending_capacity` Assignment alternative. Do not preserve a weak design merely to keep the document stable.

## Evidence boundary

Passing documentation checks would prove only that the Proposed decision record is internally present. It would not prove service extraction, concurrency safety, Position eligibility safety, cutover linearizability, migration source validity, lock-lifetime safety, availability, performance, security, or commercial readiness. Historical #64/#96 checks do not transfer to a future extraction head; every implementation candidate must obtain fresh exact-head evidence.
