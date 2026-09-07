# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding, `active` or `open` Position coverage, and the `<= 1.0000` visible seat-allocation invariant.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity/status coverage in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity/eligibility ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, `PositionEligibilityCoverage`, People-owned terminal `AssignmentAttemptOutcome`, the published/versioned cross-context capacity/attempt API or event contract, Position-eligibility fencing, capacity-revision receipts, transaction-drained writer-fenced migration, deterministic discrepancy manifest, two-service reconciliation, performance evidence, or rollback rehearsal.

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
| Give every capacity-affecting Assignment mutation its own opaque `assignment_attempt_id` | ADR 0274 domain model/protocol | proposed_design |
| Bind mutation digest to operation, exact prior Assignment version, prior reservation evidence, resulting facts, and new delta fences | ADR 0274 `AssignmentAttemptOutcome` | proposed_design |
| Make People commit Assignment create/revision/end plus terminal `committed` evidence atomically | ADR 0274 People mutation protocol | proposed_design |
| Allow unresolved post-fence capacity release only from a terminal People `aborted` tombstone that fences later commit | ADR 0274 `terminalize_attempt`/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Never shrink/release a confirmed debit from a mutable People read | ADR 0274 revision protocol | proposed_design |
| Fence positive capacity/eligibility deltas before People commits an increase, extension, or Position move | ADR 0274 `revise_assignment_capacity` | proposed_design |
| Apply decrease/shortening/end only from terminal People committed revision evidence | ADR 0274 `apply_revision_receipt` | proposed_design |
| Confirm target capacity before releasing source capacity on a Position move | ADR 0274 revision failure/recovery semantics | proposed_design |
| Bind `arm_commit_fence` to normalized complete Position eligibility coverage for the reservation interval | ADR 0274 capacity/eligibility invariant | proposed_design |
| Serialize eligibility-changing Position mutations against live fenced/confirmed debits at the same Position root | ADR 0274 `change_position_status_or_version` | proposed_design |
| Reject People-side mutable Position recheck as a correctness mechanism after a fence | ADR 0274 protocol/failure semantics | proposed_design |
| Keep People/network I/O outside Position-root transactions and row-lock lifetime | ADR 0274 protocol/failure semantics | proposed_design |
| Apply terminal People receipts in new local Organization transactions | ADR 0274 confirm/release/revision protocol | proposed_design |
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
| Prove multi-version Position coverage remains complete and fenced across version boundaries | Future Position-coverage acceptance | planned_red_green |
| Prove remote latency cannot extend Position row-lock lifetime | Future lock/I/O instrumentation acceptance | planned_operability |
| Prove crash after People create/revision commit before Organization application cannot free required capacity | Future forced-crash interleavings | planned_red_green |
| Prove increase/extension fences only positive target deltas before People revision commit | Future revision-capacity integration tests | planned_red_green |
| Prove move confirms target before source release | Future cross-Position revision tests | planned_red_green |
| Prove decrease/shortening/end cannot use stale/current read as release authority | Future revision receipt tests | planned_red_green |
| Prove stale/duplicate/out-of-order revision receipts cannot release superseded capacity | Future receipt-version tests | planned_red_green |
| Prove exact replay and same-key/different-digest rejection | Future contract/integration tests | planned_red_green |
| Prove a pre-fence legacy transaction cannot commit after projection starts | Future cutover-barrier concurrency test | planned_recovery |
| Prove deterministic migration identity/digest replay and complete projection equivalence | Future migration/recovery rehearsal | planned_recovery |
| Prove invalid legacy occupancy creates deterministic discrepancy evidence and no authority switch | Future migration failure rehearsal | planned_recovery |
| Prove migration projection equivalence and single-writer rollback | Future migration/recovery rehearsal | planned_red_green |
| Prove reserve/fence/create/terminalize/confirm/revise/apply-revision/release and Position-change buyer paths at p95 <= 20 ms under real concurrency | Future k6/E2E measurement | planned_performance |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## State-machine acceptance

The implementation must exercise, not merely document, these transitions and forbidden transitions:

| Starting state | Event/evidence | Required result |
|---|---|---|
| none | capacity-valid, Position-eligible `reserve` | `held` debit bound to one `assignment_attempt_id` |
| `held` | bounded expiry before fence | `expired`; capacity returned |
| `held` | exact `arm_commit_fence` with complete staffable Position coverage | `commit_fenced`; capacity and eligibility reserved, autonomous expiry stops |
| People attempt unresolved | initial create wins attempt serialization | Assignment and terminal `committed` outcome in one People transaction |
| People attempt unresolved | `terminalize_attempt` wins | terminal `aborted` tombstone; every later mutation for that attempt is fenced |
| People attempt `aborted` | delayed/retried mutation | no Assignment commit; replay/fail closed as aborted |
| People attempt `committed` | delayed/retried terminalization | return committed; no abort tombstone and no Organization release authority |
| `commit_fenced` | terminal People `committed` receipt obtained outside Position lock | local Organization `confirmed` transition, idempotently |
| `commit_fenced` | terminal People `aborted` receipt obtained outside Position lock | local Organization `released` transition, idempotently |
| `commit_fenced` | current Assignment absence / not-found / timeout / missing event / stale read | no release; reconciliation only |
| confirmed Assignment occupancy | proposed allocation increase or interval extension | positive Position/time-slice delta must be `commit_fenced` before People revision can commit |
| confirmed Assignment occupancy | proposed Position move | full target occupancy not already backed on target must be fenced before People revision commit |
| confirmed Assignment occupancy | decrease / shortening / end commits in People | old confirmed debit remains until exact terminal revision receipt is applied |
| committed Position move | target delta receipt | target debit is confirmed before source debit can be released |
| confirmed debit | mutable People read says smaller/ended/absent | no shrink/release; terminal revision evidence required |
| confirmed debit | stale receipt bound to superseded prior Assignment/reservation version | fail closed; debit unchanged |
| Position has effective `commit_fenced` or `confirmed` debit | proposed status/version mutation removes staffable coverage | local transaction fails closed; no People/network call while Position lock is held |
| status-change conflict recorded | governed external coordination resolves People state and durable receipts | apply receipts in separate Organization transactions, then retry exact Position command |
| `confirmed` | duplicate confirm with same version/digest | same confirmed result |
| any live debit | same idempotency key with different semantic digest | fail closed |
| legacy writer open | cutover fence enters draining epoch | no new legacy admission; snapshot waits for every pre-fence transaction to commit/rollback |
| cutover barrier closed | deterministic migration projection | every visible current/future legacy Assignment maps to stable `confirmed` reservation plus terminal committed evidence |
| drained legacy snapshot invalid or unrepresentable | migration validation | immutable deterministic discrepancy evidence; no semantic rewrite and no authority switch |

The Organization capacity calculation counts every effective `held`, `commit_fenced`, and `confirmed` debit. Existing confirmed occupancy stays counted until exact terminal People revision evidence permits reduction; positive revision deltas are counted before People can commit the larger occupancy. The same Position-root authority protects staffable eligibility for every fenced/confirmed interval. Cross-context calls happen only after local row-locking transactions end. Failures therefore bias toward temporary over-reservation rather than under-reservation or durable overbooking.

## Required failure interleavings

### Delayed create versus terminal abort

1. Organization creates and commit-fences reservation R for attempt A.
2. The Organization transaction ends and releases its Position row lock.
3. People `create_assignment(A, R)` is delayed or in flight and no Assignment is yet visible.
4. Reconciliation attempts to resolve A.
5. A read returning no Assignment must not authorize release.
6. If `terminalize_attempt(A)` records `aborted`, the delayed create must be unable to commit afterward.
7. If the delayed create commits first, it atomically records terminal `committed`; terminalization returns committed and Organization must not release R.

Passing requires exactly one terminal People outcome for A and no execution that frees Organization capacity while a later commit for A remains possible.

### Confirmed Assignment revision versus capacity adjustment

1. Assignment V1 is backed by exact confirmed reservation evidence R1.
2. Start a capacity-affecting revision attempt A2 bound to V1 and R1.
3. For an increase or interval extension, Organization fences only the positive Position/time-slice delta R2 before People may commit V2. For a Position move, Organization fences the target occupancy required by V2 before People may commit it.
4. People atomically commits V2 plus terminal `AssignmentAttemptOutcome=committed(A2)` carrying V1/R1 and R2 evidence.
5. Crash before Organization applies that receipt. R1 remains confirmed and R2 remains fenced, so capacity is conservative rather than under-reserved.
6. Recovery confirms R2 before reducing or releasing any R1 slice no longer required by V2. For a move, target is confirmed before source is released.
7. For a decrease, shortening, or end, People may commit V2 without R2, but R1 remains counted until the exact terminal V2 receipt is applied.
8. Deliver a stale or duplicate receipt from a different prior Assignment/reservation version. Organization must replay the equivalent receipt or fail closed; it must not release the current authoritative debit.
9. A mutable People read showing V2/current absence is not adjustment authority.

Passing requires every effective V2 slice to be backed throughout the transition, no slice to exceed `1.0000`, and no stale/current read to shrink a confirmed debit.

### Fenced create versus Position eligibility change

1. The reservation interval has complete `active`/`open` coverage, possibly as a normalized union of Position versions. Organization commit-fences R with the exact coverage digest, commits, and releases its Position lock.
2. People mutation is delayed before commit.
3. A concurrent Organization command proposes a version change that would make part of R's interval ineligible.
4. Organization serializes that mutation against R at the Position root and fails the local transaction closed with durable conflict evidence. It does not call People while holding the Position lock.
5. A separate governed workflow resolves People state outside any Position transaction and applies durable receipts in new local Organization transactions.
6. Only after the incompatible live debit/Assignment is resolved may the exact Position mutation be retried against current version/digest evidence.
7. If external coordination crashes, prior eligible coverage plus the existing fence remain authoritative and recovery resumes idempotently.

Passing requires no durable Assignment outside the staffable Position coverage promised by authentic capacity evidence and no remote latency extending Position row-lock lifetime.

### Legacy cutover versus in-flight mutation

1. Start a legacy People Position/Assignment capacity mutation and keep its database transaction open after admission but before commit.
2. Start cutover and atomically move the durable admission gate to the draining/fenced epoch.
3. A later legacy mutation must be rejected from admission.
4. Migration snapshot/projection remains blocked while the pre-fence transaction is unresolved.
5. Commit or roll back that transaction. Only then may the cutover barrier close and record authoritative high-water evidence.
6. Take the migration snapshot and project it twice. Both projections produce identical tenant-qualified migration identities, `confirmed` states, terminal committed evidence, normalized Position-eligibility coverage digests, and manifest digest.
7. No transaction admitted under the legacy epoch may commit after that snapshot or after Organization authority is enabled.

Passing requires an explicit linearization barrier rather than a timing heuristic, plus deterministic replay of the complete migration projection.

### Invalid legacy occupancy versus authority switch

1. Close the cutover barrier only after all pre-fence legacy transactions are terminal.
2. Use a deterministic fixture/snapshot containing a source fact that cannot be represented without changing its meaning: for example aggregate overlapping allocation above `1.0000`, incomplete staffable Position coverage, or ambiguous tenant-qualified identity.
3. Run complete projection/validation twice.
4. Both runs produce identical discrepancy identity/digest and identify the exact source fact/invariant conflict without creating replacement truth.
5. Migration does not drop, clamp, split, round, synthesize, or silently rewrite source Assignment/Position evidence.
6. Organization authority remains disabled and cutover stays fenced until governed correction is committed under the still-authoritative legacy owner and the full projection is rerun.

Passing requires migration failure to be deterministic, auditable, and lossless with respect to source truth.

## Extraction gate

Do not start Position source/schema extraction from this branch. The causal order is:

`#64 protected integration -> #96 protected integration -> #119 non-force protected adoption/integration -> ADR 0274 executable RED/GREEN owner stack -> transaction-drained writer-fenced migration -> normal protected integration`

If executable evidence invalidates the provisional commit-fence design, revise ADR 0274 while it is still Proposed and compare the two-phase `pending_capacity` Assignment alternative. Do not preserve a weak design merely to keep the document stable.

## Evidence boundary

Passing documentation checks proves only that the Proposed decision record is internally present. It does not prove service extraction, concurrency safety, revision safety, Position eligibility safety, cutover linearizability, migration source validity, lock-lifetime safety, availability, performance, security, or commercial readiness. Historical #64/#96 checks do not transfer to a future extraction head; every implementation candidate must obtain fresh exact-head evidence.
