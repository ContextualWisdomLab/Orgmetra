# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding, `active` or `open` Position coverage, and the `<= 1.0000` visible seat-allocation invariant.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity/status coverage in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity/eligibility ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, `PositionEligibilityCoverage`, People-owned terminal `AssignmentAttemptOutcome`, stable Assignment-root revision CAS, the published/versioned authenticated cross-context capacity/attempt API or event contract, owner/rollback epoch validation, Position-eligibility fencing, capacity-revision receipts, transaction-drained writer-fenced migration, deterministic discrepancy manifest, two-service reconciliation, performance evidence, or rollback rehearsal.

## Requirement matrix

| Requirement | Current evidence | State |
|---|---|---|
| Keep Position in Organization and Assignment in People | `ARCHITECTURE.md`, `docs/TRD.md` | protected_architecture |
| Preserve durable Position identity/bitemporal versions and Assignment binding | ADR 0004 | protected_accepted |
| Preserve retroactive correction across the complete currently authoritative effective-time domain | protected `docs/TRD.md` retroactive-correction rule plus ADR 0274 cutover scope | proposed_design |
| Preserve `active` or `open` Position coverage and visible seat allocation `<= 1.0000` | ADR 0005 | protected_accepted |
| Preserve union coverage when one Assignment interval spans multiple staffable Position versions | protected `validate_assignment_position_coverage` plus ADR 0274 `PositionEligibilityCoverage` | proposed_design |
| Record why synchronous availability/status-check-only is unsafe | PostgreSQL 18 §13.2 plus ADR 0274 alternative B | proposed_design |
| Define one canonical capacity/eligibility authority without cross-service SQL | ADR 0274 option C | proposed_design |
| Make `held` consume capacity but allow bounded autonomous expiry before commit fence | ADR 0274 capacity invariant/protocol | proposed_design |
| Make `commit_fenced` consume capacity without autonomous expiry | ADR 0274 protocol/failure semantics | proposed_design |
| Give every capacity-affecting Assignment mutation its own opaque `assignment_attempt_id` | ADR 0274 domain model/protocol | proposed_design |
| Bind reserve idempotency record and semantic digest to the exact `assignment_attempt_id`; reject same-key/different-attempt | ADR 0274 `reserve`/`arm_commit_fence` | proposed_design |
| Bind mutation digest to stable Assignment identity, operation, exact attempt ID, expected prior Assignment version, prior reservation evidence, resulting facts, and new delta fences | ADR 0274 `AssignmentAttemptOutcome` | proposed_design |
| Bind each terminal receipt to exact target reservation identity/version/digest and fence disposition (`consumed` or `unused_releasable`) | ADR 0274 terminal outcome/revision protocol | proposed_design |
| Authenticate durable cross-context receipts by canonical signature, issuer/audience, tenant, contract version, authority/rollback epoch, receipt identity, and exact target payload before write authority | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Preserve idempotent equivalent receipt replay while rejecting same-receipt-ID/different-payload, stale-epoch, forged, wrong-audience, or cross-tenant evidence | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Serialize revisions/ends at the stable Assignment root and compare-and-set the expected prior version | ADR 0274 `revise_assignment_capacity` | proposed_design |
| Make People commit Assignment create/revision/end plus terminal `committed` evidence atomically | ADR 0274 People mutation protocol | proposed_design |
| Make a stale-predecessor revision terminally non-committing so its unused delta fences have exact abort/conflict release evidence | ADR 0274 revision protocol | proposed_design |
| Allow unresolved post-fence capacity release only from an authenticated terminal People `aborted` tombstone that fences later commit | ADR 0274 `terminalize_attempt`/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Never shrink/release a confirmed debit from a mutable People read | ADR 0274 revision protocol | proposed_design |
| Fence positive capacity/eligibility deltas before People commits an increase, extension, or Position move | ADR 0274 `revise_assignment_capacity` | proposed_design |
| Apply decrease/shortening/end only from authenticated terminal People committed revision evidence | ADR 0274 `apply_revision_receipt` | proposed_design |
| Confirm target capacity before releasing source capacity on a Position move | ADR 0274 revision failure/recovery semantics | proposed_design |
| Bind `arm_commit_fence` to normalized complete Position eligibility coverage for the reservation interval | ADR 0274 capacity/eligibility invariant | proposed_design |
| Serialize eligibility-changing Position mutations against live fenced/confirmed debits at the same Position root | ADR 0274 `change_position_status_or_version` | proposed_design |
| Reject People-side mutable Position recheck as a correctness mechanism after a fence | ADR 0274 protocol/failure semantics | proposed_design |
| Keep cross-context I/O outside Position-root and Assignment-root transaction/lock lifetime | ADR 0274 protocol/failure semantics | proposed_design |
| Apply terminal People receipts in new local Organization transactions | ADR 0274 confirm/release/revision protocol | proposed_design |
| Fail conflicting Position changes locally, resolve People state outside the lock, then retry on exact version/digest evidence | ADR 0274 status-change protocol | proposed_design |
| Keep Person/Employment payload and unrelated PII out of Organization capacity evidence | ADR 0274 domain model | proposed_design |
| Prevent dual Position/capacity writers during extraction | ADR 0274 cutover/rollback | proposed_design |
| Drain every pre-fence legacy mutation before taking the migration snapshot | ADR 0274 cutover barrier | proposed_design |
| Increment and pin authority/rollback epochs across cutover or rollback so superseded receipts cannot authorize writes | ADR 0274 cutover/rollback + receipt envelope | proposed_security_design |
| Deterministically map each currently authoritative legacy Assignment, including wholly past-effective occupancy, to confirmed reservation/terminal committed migration evidence | ADR 0274 cutover manifest | proposed_design |
| Keep superseded recorded-history versions as People/audit provenance without duplicating them as simultaneously live capacity debits | ADR 0274 cutover projection rule | proposed_design |
| Fail cutover instead of rewriting an invalid/unrepresentable legacy fact to fit the target ledger | ADR 0274 cutover discrepancy rule | proposed_design |
| Preserve current People mutation behavior while prerequisites remain mutable | #64 owner path; no extraction source in this slice | active_owner_boundary |
| Preserve Organization hierarchy prerequisite delta before extraction | #96 -> #119 owner order | active_owner_boundary |
| Prove concurrent overlapping capacity cannot exceed `1.0000` | Future two-service/PostgreSQL acceptance | planned_red_green |
| Prove delayed create versus terminal abort cannot produce both an aborted receipt and later committed Assignment | Future People attempt-race acceptance | planned_red_green |
| Prove two different revisions based on the same Assignment predecessor cannot both advance the lineage | Future Assignment-root CAS acceptance | planned_red_green |
| Prove stale-predecessor abort/conflict releases only that attempt's exact unused delta fences | Future Assignment-root/capacity integration | planned_red_green |
| Prove duplicate/reordered revision receipts cannot apply a disposition to the wrong reservation version | Future receipt-version/disposition tests | planned_red_green |
| Prove same idempotency key with a different `assignment_attempt_id` fails closed | Future contract/integration tests | planned_red_green |
| Prove forged signature, wrong issuer/audience, cross-tenant receipt, stale authority/rollback epoch, and mismatched target/version/digest fail closed | Future cross-context security tests | planned_security |
| Prove equivalent authenticated receipt replay is idempotent while same-receipt-ID/different-payload replay fails closed | Future cross-context security/idempotency tests | planned_security |
| Prove Position close/status mutation cannot invalidate eligibility while an authentic fenced create can still commit | Future Position-status-vs-create race acceptance | planned_red_green |
| Prove multi-version Position coverage remains complete and fenced across version boundaries | Future Position-coverage acceptance | planned_red_green |
| Prove remote latency cannot extend Position or Assignment root-lock lifetime | Future lock/I/O instrumentation acceptance | planned_operability |
| Prove crash after People create/revision commit before Organization application cannot free required capacity | Future forced-crash interleavings | planned_red_green |
| Prove increase/extension fences only positive target deltas before People revision commit | Future revision-capacity integration tests | planned_red_green |
| Prove move confirms target before source release | Future cross-Position revision tests | planned_red_green |
| Prove decrease/shortening/end cannot use stale/current read as release authority | Future revision receipt tests | planned_red_green |
| Prove stale/duplicate/out-of-order revision receipts cannot release superseded capacity | Future receipt-version tests | planned_red_green |
| Prove exact replay and same-key/different-digest rejection | Future contract/integration tests | planned_red_green |
| Prove a pre-fence legacy transaction cannot commit after projection starts | Future cutover-barrier concurrency test | planned_recovery |
| Prove deterministic migration identity/digest replay and complete projection equivalence across past/present/future effective slices | Future migration/recovery rehearsal | planned_recovery |
| Prove a post-cutover retroactive correction sees migrated historical Position occupancy and cannot exceed `1.0000` | Future retroactive-correction migration acceptance | planned_recovery |
| Prove invalid legacy occupancy creates deterministic discrepancy evidence and no authority switch | Future migration failure rehearsal | planned_recovery |
| Prove migration projection equivalence and single-writer rollback | Future migration/recovery rehearsal | planned_red_green |
| Prove reserve/fence/create/terminalize/confirm/revise/apply-revision/release and Position-change buyer paths at p95 <= 20 ms under real concurrency | Future k6/E2E measurement | planned_performance |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## State-machine acceptance

The implementation must exercise, not merely document, these transitions and forbidden transitions:

| Starting state | Event/evidence | Required result |
|---|---|---|
| none | capacity-valid, Position-eligible `reserve` | `held` debit bound to one `assignment_attempt_id` |
| no prior idempotency record | key K + attempt A + digest D | persist K/A/D and resulting reservation identity/version |
| existing idempotency K/A/D | exact replay | same reservation/result idempotently |
| existing idempotency key K | same digest intent but different attempt B | fail closed; no aliasing of B onto A's reservation |
| `held` | bounded expiry before fence | `expired`; capacity returned |
| `held` | exact `arm_commit_fence` with matching attempt/digest/version and complete staffable Position coverage | `commit_fenced`; capacity and eligibility reserved, autonomous expiry stops |
| `held` | arm request with mismatched attempt/digest/expected reservation version | fail closed; state unchanged |
| People pre-write | valid signed Organization receipt with exact issuer/audience/tenant/epoch/attempt/reservation target | receipt may proceed to domain validation |
| People pre-write | forged signature, wrong issuer/audience, cross-tenant, stale authority/rollback epoch, or mismatched reservation target | fail closed before Assignment mutation |
| any receipt consumer | byte-equivalent replay of same `receipt_id` and payload | same result idempotently |
| any receipt consumer | same `receipt_id` with different payload/attempt/target/epoch | fail closed as contradictory evidence |
| People attempt unresolved | initial create wins attempt serialization | Assignment and terminal `committed` outcome in one People transaction |
| People attempt unresolved | `terminalize_attempt` wins | terminal `aborted` tombstone; every later mutation for that attempt is fenced |
| People attempt `aborted` | delayed/retried mutation | no Assignment commit; replay/fail closed as aborted |
| People attempt `committed` | delayed/retried terminalization | return committed; no abort tombstone and no Organization release authority |
| `commit_fenced` | authenticated terminal People `committed` receipt with matching target version and `consumed` disposition | local Organization `confirmed` transition by expected-version CAS, idempotently |
| `commit_fenced` | authenticated terminal People `aborted` receipt with matching target version and `unused_releasable` disposition | local Organization `released` transition by expected-version CAS, idempotently |
| `commit_fenced` | current Assignment absence / not-found / timeout / missing event / stale read | no release; reconciliation only |
| Assignment V1 | revision A2 and revision A3 both expect V1 | stable Assignment-root serialization/CAS permits at most one new authoritative successor; stale loser is terminally non-committing |
| stale-predecessor revision attempt | exact authenticated terminal abort/conflict receipt | only target reservations marked `unused_releasable` at the exact expected versions may be released idempotently |
| confirmed Assignment occupancy | proposed allocation increase or interval extension | positive Position/time-slice delta must be `commit_fenced` before People revision can commit |
| confirmed Assignment occupancy | proposed Position move | full target occupancy not already backed on target must be fenced before People revision commit |
| confirmed Assignment occupancy | decrease / shortening / end commits in People | old confirmed debit remains until exact terminal revision receipt is applied |
| committed Position move | authenticated target delta receipt | target debit is confirmed before source debit can be released |
| confirmed debit | mutable People read says smaller/ended/absent | no shrink/release; terminal revision evidence required |
| confirmed debit | stale receipt bound to superseded prior Assignment/reservation version | fail closed; debit unchanged |
| Position has effective `commit_fenced` or `confirmed` debit | proposed status/version mutation removes staffable coverage | local transaction fails closed; no People/network call while Position lock is held |
| status-change conflict recorded | governed external coordination resolves People state and durable receipts | apply receipts in separate Organization transactions, then retry exact Position command |
| `confirmed` | duplicate confirm with same authenticated version/digest/disposition | same confirmed result |
| any live debit | same idempotency key with different semantic digest | fail closed |
| legacy writer open | cutover fence enters draining epoch | no new legacy admission; snapshot waits for every pre-fence transaction to commit/rollback |
| cutover/rollback authority switch | owner epoch pair increments | receipts from superseded authority/rollback epoch no longer authorize writes |
| cutover barrier closed | deterministic migration projection | every currently recorded-visible legacy Assignment across the complete effective-time domain, including wholly past intervals, maps to stable `confirmed` reservation plus terminal committed evidence |
| post-cutover historical slice | retroactive create/correction overlaps migrated past-effective occupancy | historical migrated debit participates in capacity/eligibility validation; no slice may exceed `1.0000` or bypass staffable coverage |
| drained legacy snapshot invalid or unrepresentable | migration validation | immutable deterministic discrepancy evidence; no semantic rewrite and no authority switch |

The Organization capacity calculation counts every effective `held`, `commit_fenced`, and `confirmed` debit. Existing confirmed occupancy stays counted until exact authenticated terminal People revision evidence permits reduction; positive revision deltas are counted before People can commit the larger occupancy. People independently serializes the stable Assignment lineage and rejects stale expected predecessors, so two distinct attempt IDs cannot fork one Assignment root. The same Position-root authority protects staffable eligibility for every fenced/confirmed interval. Cross-context calls happen only after local row-locking transactions end. Failures therefore bias toward temporary over-reservation rather than under-reservation or durable overbooking.

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

### Concurrent revisions from the same Assignment predecessor

1. Assignment V1 is authoritative and backed by confirmed reservation evidence R1.
2. Prepare mutation attempts A2 and A3 independently, both digest-bound to stable Assignment identity, expected prior V1 and R1. Let each obtain any positive delta fence it needs.
3. Start both People transactions concurrently.
4. People serializes the same stable Assignment root. The winner verifies V1 is still authoritative and may atomically commit V2 plus terminal `committed` outcome.
5. The loser resumes after the root lock, finds its expected prior V1 is stale, and must not commit V3 from V1. It records/returns terminal `aborted` conflict evidence for that attempt.
6. Each terminal receipt identifies every target delta reservation by exact identity/version/digest and marks its disposition. Deliver the winner and loser receipts duplicated and out of order. Organization may confirm only the winner's `consumed` fences and may release only the loser's `unused_releasable` fences by expected-version CAS; a receipt for another reservation version cannot mutate the current debit.
7. A timeout, mutable current read, or knowledge that another revision won is not release authority.
8. Retrying the user's intended correction requires a new attempt bound to the now-authoritative Assignment version and current reservation evidence.

Passing requires a single Assignment lineage successor from V1, no orphaned under-reserved committed revision, and no wrong-version or wrong-disposition fence mutation under duplicate/reordered receipts.

### Authenticated receipt rejection and replay

1. Create one valid Organization `commit_fenced` receipt for tenant T, audience `people_core`, attempt A, reservation R@V, current authority/rollback epoch E, and semantic payload digest D.
2. Verify the valid signature and exact target, then replay the byte-equivalent receipt. The second delivery returns the same result idempotently.
3. Independently mutate one field at a time without a valid re-sign: signature, issuer, audience, tenant, attempt, reservation identity/version, eligibility digest, semantic digest, authority epoch, rollback epoch, or contract version. Every variant fails before People write authorization.
4. Re-sign a structurally valid receipt under a superseded but previously trusted owner epoch/key. It still fails because the consumer pins the current authority/rollback epoch.
5. Reuse the original `receipt_id` with a different canonical payload and valid signature. It fails as contradictory replay evidence rather than aliasing to the prior result.
6. Repeat symmetrically for People terminal receipts consumed by Organization, including wrong target reservation version and wrong `consumed`/`unused_releasable` disposition.

Passing requires cryptographic source/integrity verification plus semantic target/epoch validation in both directions; transport success, wall-clock recency, or a valid signature alone is insufficient.

### Confirmed Assignment revision versus capacity adjustment

1. Assignment V1 is backed by exact confirmed reservation evidence R1.
2. Start a capacity-affecting revision attempt A2 bound to stable Assignment identity, expected prior V1 and R1.
3. For an increase or interval extension, Organization fences only the positive Position/time-slice delta R2 before People may commit V2. For a Position move, Organization fences the target occupancy required by V2 before People may commit it.
4. People serializes the Assignment root, confirms V1 is still authoritative, then atomically commits V2 plus terminal `AssignmentAttemptOutcome=committed(A2)` carrying V1/R1 and exact target reservation versions/digests/dispositions for R2.
5. Crash before Organization applies that receipt. R1 remains confirmed and R2 remains fenced, so capacity is conservative rather than under-reserved.
6. Recovery authenticates the receipt, confirms R2 by expected-version CAS before reducing or releasing any R1 slice no longer required by V2. For a move, target is confirmed before source is released.
7. For a decrease, shortening, or end, People may commit V2 without R2, but R1 remains counted until the exact authenticated terminal V2 receipt is applied.
8. Deliver a stale or duplicate receipt from a different prior Assignment/reservation version or with a contradictory fence disposition. Organization must replay the equivalent receipt or fail closed; it must not release the current authoritative debit.
9. A mutable People read showing V2/current absence is not adjustment authority.

Passing requires every effective V2 slice to be backed throughout the transition, no slice to exceed `1.0000`, and no stale/current read or wrong-version/disposition receipt to shrink a confirmed debit.

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
6. Take the migration snapshot and project it twice across every currently recorded-visible Assignment in the complete effective-time domain, including wholly past-effective occupancy. Both projections produce identical tenant-qualified migration identities, `confirmed` states, terminal committed evidence, normalized Position-eligibility coverage digests, and manifest digest; superseded recorded-history versions remain provenance and do not appear as duplicate live debits.
7. Switch authority/rollback epoch and verify that a correctly signed receipt from the superseded epoch is rejected by the new consumer authority.
8. No transaction admitted under the legacy epoch may commit after that snapshot or after Organization authority is enabled.

Passing requires an explicit linearization barrier rather than a timing heuristic, deterministic replay of the complete currently authoritative effective-time projection, and rejection of superseded-epoch write authority.

### Retroactive correction versus migrated historical occupancy

1. In the drained legacy snapshot, keep one currently recorded-visible Assignment on Position P whose effective interval is wholly before the cutover date and whose allocation is `0.6000`.
2. Project that past-effective Assignment to a deterministic `confirmed` Organization debit while keeping superseded recorded-history versions only as People/audit provenance.
3. Switch to the new single-writer authority and submit a retroactive create/correction that would add another overlapping `0.6000` on P for the same historical slice.
4. Organization must include the migrated historical debit in the Position-root capacity calculation and reject the new claim because the effective total would be `1.2000`.
5. Repeat with a retroactive change whose historical interval lacks `active`/`open` Position coverage. The capacity/eligibility protocol must fail closed rather than treating the past interval as outside ledger scope.
6. A migration implementation that projected only current/future-effective assignments is the RED counterexample: it would see no historical debit and could authorize a false `0.6000` availability result.

Passing requires post-cutover retroactive bitemporal writes to observe the same currently authoritative historical capacity and Position-eligibility truth that protected `develop` requires before extraction.

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

Passing documentation checks proves only that the Proposed decision record is internally present. It does not prove service extraction, concurrency safety, Assignment-lineage serialization, revision safety, Position eligibility safety, cutover linearizability, complete historical migration scope for retroactive correction, migration source validity, lock-lifetime safety, authenticated-receipt security, availability, performance, or commercial readiness. Historical #64/#96 checks do not transfer to a future extraction head; every implementation candidate must obtain fresh exact-head evidence.
