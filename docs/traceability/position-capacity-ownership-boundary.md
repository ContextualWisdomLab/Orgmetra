# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding, `active` or `open` Position coverage, and the `<= 1.0000` visible seat-allocation invariant.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity/status coverage in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity/eligibility ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, `PositionEligibilityCoverage`, People-owned terminal `AssignmentAttemptOutcome`, stable Assignment-root revision CAS, the published/versioned authenticated cross-context capacity/attempt API or event contract, owner/rollback epoch validation, Position-eligibility fencing, capacity-revision receipts, transaction-drained writer-fenced migration, live-protocol quiescence before epoch retirement, deterministic discrepancy manifest, two-service reconciliation, performance evidence, or rollback rehearsal.

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
| Bind reserve idempotency and semantic digest to exact attempt and authority context | ADR 0274 `reserve`/`arm_commit_fence` | proposed_design |
| Bind mutation digest to Assignment identity, operation, attempt, expected prior version, reservation evidence, result facts, and delta fences | ADR 0274 `AssignmentAttemptOutcome` | proposed_design |
| Bind each terminal receipt to exact target reservation identity/version/digest and fence disposition | ADR 0274 terminal outcome/revision protocol | proposed_design |
| Authenticate durable cross-context receipts by canonical signature, issuer/audience, tenant, contract version, authority/rollback epoch, receipt identity, and exact target payload | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Preserve idempotent equivalent receipt replay while rejecting reused-ID/different-payload, retired-epoch, forged, wrong-audience, or cross-tenant evidence | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Keep historical old-epoch receipts verifiable for audit without restoring retired write authority | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Serialize revisions/ends at stable Assignment root and CAS expected prior version | ADR 0274 `revise_assignment_capacity` | proposed_design |
| Make People commit Assignment mutation plus terminal `committed` evidence atomically | ADR 0274 People mutation protocol | proposed_design |
| Make stale-predecessor revision terminally non-committing so unused delta fences have exact release evidence | ADR 0274 revision protocol | proposed_design |
| Allow unresolved post-fence release only from authenticated terminal People `aborted` evidence that fences later commit | ADR 0274 terminalize/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Never shrink/release a confirmed debit from a mutable People read | ADR 0274 revision protocol | proposed_design |
| Fence positive capacity/eligibility deltas before People commits increase, extension, or Position move | ADR 0274 revision protocol | proposed_design |
| Apply decrease/shortening/end only from authenticated terminal People committed revision evidence | ADR 0274 `apply_revision_receipt` | proposed_design |
| Confirm target capacity before releasing source capacity on Position move | ADR 0274 revision failure/recovery semantics | proposed_design |
| Bind commit fence to normalized complete Position eligibility coverage | ADR 0274 capacity/eligibility invariant | proposed_design |
| Serialize eligibility-changing Position mutations against live fenced/confirmed debits at same Position root | ADR 0274 status-change protocol | proposed_design |
| Reject People-side mutable Position recheck as post-fence correctness mechanism | ADR 0274 protocol/failure semantics | proposed_design |
| Keep cross-context I/O outside Position-root and Assignment-root transactions | ADR 0274 protocol/failure semantics | proposed_design |
| Apply terminal People receipts in new local Organization transactions | ADR 0274 confirm/release/revision protocol | proposed_design |
| Keep Person/Employment and unrelated PII out of Organization capacity evidence | ADR 0274 domain model | proposed_design |
| Prevent dual Position/capacity writers during extraction | ADR 0274 cutover/rollback | proposed_design |
| Drain every pre-fence legacy mutation before initial migration snapshot | ADR 0274 initial cutover barrier | proposed_design |
| Deterministically map every current legacy Assignment, including wholly past-effective occupancy, to confirmed reservation/terminal committed evidence | ADR 0274 cutover manifest | proposed_design |
| Keep superseded recorded-history as provenance without duplicate live debits | ADR 0274 projection rule | proposed_design |
| Fail cutover instead of rewriting invalid/unrepresentable legacy truth | ADR 0274 discrepancy rule | proposed_design |
| Before retiring a live protocol epoch, stop new Organization reservation/fence admissions under that epoch | ADR 0274 protocol-quiescence sequence | proposed_recovery_design |
| Before retiring a live protocol epoch, stop new People mutation admissions from that epoch and drain every already-admitted People transaction | ADR 0274 protocol-quiescence sequence | proposed_recovery_design |
| Settle every retiring-epoch `commit_fenced` attempt to terminal People evidence and apply its exact capacity disposition before snapshot | ADR 0274 protocol-quiescence sequence | proposed_recovery_design |
| Apply pending retiring-epoch confirm/release/revision receipts until Organization confirmed capacity and People Assignment truth are equivalent | ADR 0274 protocol-quiescence manifest | proposed_recovery_design |
| Prove zero unresolved fenced state and zero unapplied capacity-changing terminal outcomes before authority/rollback epoch rollover | ADR 0274 protocol-quiescence manifest | proposed_recovery_design |
| Reject retired-epoch receipts for new writes only after protocol state has been settled, not as a substitute for settlement | ADR 0274 epoch transition | proposed_security_recovery_design |
| Preserve current People mutation behavior while prerequisites remain mutable | #64 owner path; no extraction source in this slice | active_owner_boundary |
| Preserve Organization hierarchy prerequisite delta before extraction | #96 -> #119 owner order | active_owner_boundary |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## Planned executable evidence

| Claim | Required evidence | State |
|---|---|---|
| Concurrent overlapping capacity cannot exceed `1.0000` | real two-service/PostgreSQL race | planned_red_green |
| Delayed create versus terminal abort has one terminal People outcome | forced attempt-race acceptance | planned_red_green |
| Two revisions from same Assignment predecessor cannot both advance lineage | Assignment-root CAS race | planned_red_green |
| Stale-predecessor abort releases only exact unused delta fences | Assignment-root/capacity integration | planned_red_green |
| Duplicate/reordered revision receipt cannot affect wrong reservation version | receipt-version/disposition tests | planned_red_green |
| Same key with different attempt or digest fails closed | contract/integration tests | planned_red_green |
| Forged/wrong-audience/cross-tenant/retired-epoch/wrong-target receipts fail closed | cross-context security tests | planned_security |
| Equivalent receipt replay is idempotent while same-ID/different-payload fails | security/idempotency tests | planned_security |
| Position close cannot invalidate eligibility while authentic fence can still commit | Position-status-vs-create race | planned_red_green |
| Multi-version Position coverage stays complete/fenced | Position-coverage acceptance | planned_red_green |
| Remote latency cannot extend local root-lock lifetime | lock/I/O instrumentation | planned_operability |
| Crash after People commit before Organization application cannot free required capacity | forced-crash interleaving | planned_red_green |
| Increase/extension fences only positive target deltas before People commit | revision-capacity integration | planned_red_green |
| Move confirms target before source release | cross-Position revision tests | planned_red_green |
| Decrease/shortening/end cannot use current read as release authority | revision-receipt tests | planned_red_green |
| Pre-fence legacy transaction cannot commit after projection starts | cutover-barrier race | planned_recovery |
| Migration identity/digest replay is deterministic across full effective-time projection | migration/recovery rehearsal | planned_recovery |
| Retroactive correction sees migrated historical occupancy | historical correction acceptance | planned_recovery |
| Invalid legacy occupancy creates discrepancy evidence and no authority switch | migration failure rehearsal | planned_recovery |
| Retiring epoch cannot switch while one `commit_fenced` attempt is unresolved | protocol-quiescence rollback race | planned_recovery |
| Delayed old-epoch mutation cannot enter after People admission barrier closes | protocol admission/drain race | planned_recovery |
| Every old-epoch admitted mutation finishes before terminalization/snapshot | transaction-lifetime protocol admission receipt test | planned_recovery |
| Quiescence manifest proves zero unresolved fences/unapplied terminal outcomes and cross-owner equivalence | recovery manifest rehearsal | planned_recovery |
| After epoch rollover, old receipt cannot mutate state and no old debit is orphaned | epoch security/recovery test | planned_security_recovery |
| Migration projection equivalence and single-writer rollback | recovery rehearsal | planned_red_green |
| Buyer paths meet p95 <= 20 ms under real concurrency | k6/E2E measurement | planned_performance |

## State-machine acceptance

| Starting state | Event/evidence | Required result |
|---|---|---|
| none | capacity-valid, Position-eligible `reserve` | `held` debit bound to one attempt and issuing epoch |
| no prior idempotency record | key K + attempt A + digest D + epoch E | persist K/A/D/E and resulting reservation identity/version |
| existing idempotency K/A/D/E | exact replay | same reservation/result idempotently |
| existing idempotency key K | same semantic intent but different attempt/digest/authority context | fail closed |
| `held` | bounded expiry before fence | `expired`; capacity returned |
| `held` | exact commit fence with matching attempt/digest/version/current epoch and complete coverage | `commit_fenced`; autonomous expiry stops |
| `held` | mismatched attempt/digest/version/retired epoch | fail closed; state unchanged |
| People pre-write | valid signed Organization receipt with exact current issuer/audience/tenant/epoch/attempt/target | proceed to domain validation |
| People pre-write | forged/wrong-audience/cross-tenant/retired-epoch/mismatched target | fail closed before Assignment mutation |
| any receipt consumer | equivalent replay of already accepted terminal result | same result idempotently |
| any receipt consumer | same receipt ID with different payload/attempt/target/epoch | contradictory evidence; fail closed |
| People attempt unresolved | create wins attempt serialization | Assignment + terminal `committed` atomically |
| People attempt unresolved | terminalization wins | terminal `aborted`; later mutation cannot commit |
| People attempt `aborted` | delayed/retried mutation | no Assignment commit |
| People attempt `committed` | delayed/retried terminalization | return committed; no release authority |
| `commit_fenced` | exact terminal committed receipt with `consumed` | Organization `confirmed` by expected-version CAS |
| `commit_fenced` | exact terminal aborted receipt with `unused_releasable` | Organization `released` by expected-version CAS |
| `commit_fenced` | current absence/not-found/timeout/missing event | no release; reconciliation only |
| Assignment V1 | concurrent revisions A2/A3 both expect V1 | stable root/CAS permits at most one successor |
| stale-predecessor attempt | exact abort/conflict receipt | only exact `unused_releasable` targets may release |
| confirmed occupancy | increase/extension | positive Position/time delta fenced before People commit |
| confirmed occupancy | Position move | target occupancy fenced before People commit |
| confirmed occupancy | decrease/shortening/end commits in People | old debit stays until terminal revision receipt applied |
| committed Position move | authenticated target receipt | target confirmed before source release |
| confirmed debit | mutable People read says smaller/ended/absent | no shrink/release |
| Position has fenced/confirmed debit | status mutation removes staffable coverage | local fail-closed; no remote call under lock |
| legacy writer open | initial cutover enters draining epoch | reject new legacy admission; wait for all old transactions |
| epoch E Organization protocol open | begin retiring E | no new E reservation or fence admission |
| epoch E People protocol open | enter People `draining(E)` | no new E receipt-authorized mutation; wait for admitted transactions |
| E `held` after People drain | ordinary safe release/expiry | settle to non-consuming state before rollover |
| E `commit_fenced` after People drain | terminalize/reconcile exact attempt | terminal committed/aborted outcome, then apply exact disposition |
| E terminal revision/confirm/release receipt pending | quiescence settlement | apply by exact-version CAS before snapshot |
| retiring E still has unresolved fence or unapplied capacity-changing outcome | attempted snapshot/epoch increment | block transition |
| retiring E quiescence manifest has zero unresolved protocol state and cross-owner equivalence | epoch increment | allow exactly one target authority; E no longer authorizes new transitions |
| retired E | otherwise valid historical receipt arrives | audit/replay existing terminal result only; no new domain transition |
| cutover barrier closed | deterministic migration projection | full effective-time Assignment truth maps to stable confirmed reservation evidence |
| post-cutover historical slice | retroactive overlapping write | migrated historical debit participates; no capacity/coverage bypass |
| drained legacy snapshot invalid | migration validation | deterministic discrepancy evidence; no switch |

## Required failure interleavings

### Delayed create versus terminal abort

1. Organization creates and commit-fences reservation R for attempt A.
2. People `create_assignment(A, R)` is delayed or in flight.
3. Reconciliation attempts to resolve A.
4. A read returning no Assignment does not authorize release.
5. If `terminalize_attempt(A)` records `aborted`, delayed create cannot commit afterward.
6. If create commits first, it atomically records terminal `committed`; terminalization returns committed and Organization must not release R.

Passing requires exactly one terminal People outcome and no execution that frees capacity while a later commit remains possible.

### Concurrent revisions from one predecessor

1. Assignment V1 is authoritative and backed by confirmed reservation R1.
2. Prepare A2 and A3 independently, both bound to V1/R1; each may obtain positive delta fences.
3. Run People transactions concurrently.
4. Stable Assignment-root serialization lets at most one verify V1 and commit a successor.
5. Loser sees stale V1 and records terminal non-committing conflict evidence.
6. Deliver winner/loser receipts duplicated and out of order. Organization confirms only winner `consumed` fences and releases only loser `unused_releasable` fences at exact expected reservation versions.

Passing requires one lineage successor, no under-reserved committed revision, and no wrong-target capacity mutation.

### Authenticated receipt rejection and replay

1. Create a valid current-epoch Organization fence receipt for tenant T, People audience, attempt A, reservation R@V, semantic digest D.
2. Verify it and replay the equivalent receipt; replay yields the same result.
3. Mutate signature, issuer, audience, tenant, attempt, target version, coverage digest, semantic digest, contract version, or epoch without valid authority; every variant fails before write.
4. Present a correctly signed receipt from a retired epoch; it cannot authorize a new transition.
5. Reuse one receipt ID with a different canonical payload; fail as contradictory replay.
6. Repeat symmetrically for People terminal receipts consumed by Organization.

Historical signature verification is audit evidence, not revival of retired write authority.

### Confirmed revision versus capacity adjustment

1. V1 is backed by confirmed R1.
2. Start A2 bound to V1/R1.
3. Fence positive delta R2 before any increase/extension/move can commit.
4. People CASes V1 and atomically commits V2 plus terminal outcome.
5. Crash before Organization application; R1 stays confirmed and R2 stays fenced.
6. Recovery confirms R2 before reducing/releasing superseded R1 slices.
7. Decrease/shortening/end may commit without R2, but R1 remains counted until exact terminal V2 receipt is applied.

Passing requires all V2 slices to stay backed throughout transition and stale/current reads never to shrink capacity.

### Fenced create versus Position eligibility change

1. Organization fences R with complete normalized eligible coverage and commits.
2. People mutation is delayed.
3. Concurrent Organization command proposes an ineligible Position change.
4. Same Position-root serialization sees R and fails closed locally without People/network I/O under lock.
5. External coordination resolves People state outside the lock and applies durable receipts in new Organization transactions before retry.

Passing requires no durable Assignment outside promised staffable coverage and no remote latency extending Position lock lifetime.

### Initial legacy cutover versus in-flight mutation

1. Hold one admitted legacy Position/Assignment transaction open.
2. Move durable legacy admission gate to draining/fenced.
3. Reject later legacy mutation admission.
4. Snapshot remains blocked until the pre-fence transaction commits/rolls back.
5. Project the complete current effective-time truth twice; identities/digests/manifests are identical.
6. Validate all source facts losslessly before enabling Organization authority.

Passing requires an explicit transaction linearization barrier, deterministic projection, and no legacy commit after the snapshot.

### Live epoch retirement versus unresolved fenced attempt

This is the RED that distinguishes protocol quiescence from ordinary database transaction drain.

1. Under epoch E, Organization creates and commit-fences R for attempt A; Organization transaction ends. People has not yet made A terminal.
2. Start rollback/epoch retirement. Organization enters `draining(E)` and stops issuing new E reservations/fences.
3. People enters `draining(E)` for E receipt-authorized mutations. Intentionally delay one E create before admission and hold another already-admitted E People transaction open.
4. The delayed-but-not-admitted request must no longer enter. The already-admitted transaction must keep the quiescence barrier open until it commits or rolls back.
5. After admitted People transactions drain, reconcile A. `terminalize_attempt(A)` may now safely establish `aborted` if no admitted create committed, or it returns `committed` if one did. Exactly one terminal outcome exists.
6. Apply A's exact terminal receipt to Organization. Repeat for every E fence and every pending E capacity-changing terminal receipt.
7. Attempt to take the rollback snapshot while any E `commit_fenced` debit or unapplied E capacity-changing terminal outcome remains. The attempt must fail closed.
8. Build a deterministic quiescence manifest and prove zero unresolved E `commit_fenced` debits, zero unapplied capacity-changing E outcomes, and equivalence between Organization confirmed occupancy and authoritative People Assignment truth.
9. Only now take the authoritative rollback snapshot, project the chosen target writer, and increment authority/rollback epoch.
10. Deliver an otherwise authentic E receipt after rollover. It may support audit or replay of an already-durable terminal result but cannot authorize a new Assignment or capacity transition.

Passing requires no after-snapshot old-epoch mutation and no orphaned old-epoch debit/attempt. Rejecting E receipts is the final authority boundary, not a substitute for pre-switch settlement.

### Retroactive correction versus migrated historical occupancy

1. Legacy snapshot contains a currently recorded-visible wholly past Assignment on P at `0.6000`.
2. Project it to deterministic confirmed Organization debit while keeping superseded recorded history only as provenance.
3. After cutover, submit a retroactive overlapping `0.6000` claim.
4. Organization counts migrated historical debit and rejects `1.2000` total.
5. Repeat where historical interval lacks staffable Position coverage; fail closed.

Passing requires post-cutover retroactive writes to observe the same authoritative historical capacity and eligibility truth.

### Invalid legacy occupancy versus authority switch

1. Drain all pre-fence legacy transactions.
2. Use a deterministic source snapshot containing an unrepresentable fact: over-allocation, incomplete coverage, or ambiguous tenant identity.
3. Run projection/validation twice.
4. Both runs emit the same discrepancy identity/digest and do not create replacement truth.
5. Keep Organization authority disabled until governed correction is committed under the still-authoritative legacy owner and full projection is rerun.

Passing requires migration failure to be deterministic, auditable, and lossless with respect to source truth.