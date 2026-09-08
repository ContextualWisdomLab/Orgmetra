# Position capacity-ownership traceability

## Truth classification

- **Protected `develop` truth:** `people_core` owns Assignment; accepted architecture assigns Position to `organization_core`; ADR 0004/0005 define bitemporal Position/Assignment binding, `active` or `open` Position coverage, the `<= 1.0000` visible Position-seat invariant, and ADR 0004 permits multiple concurrent Assignments only while one Employment's allocation remains at or below `1.0000`.
- **Current executable protected truth:** the shipped People mutation boundary still owns Position creation and enforces Assignment capacity/status coverage in the same PostgreSQL mutation path. There is no protected executable `organization_core` service yet.
- **Active-PR truth:** ADR 0274 specifies a Proposed Position-capacity/eligibility ownership protocol only. It adds no runtime owner, schema, API, migration, or claim of distributed correctness.
- **Prerequisite active truth:** #64 owns the current People mutation/concurrency hardening; #96 and #119 own the Organization prerequisite stack. ADR 0274 must not copy their mutable source.
- **Not yet implemented:** `PositionCapacityReservation`, `PositionEligibilityCoverage`, People-owned terminal `AssignmentAttemptOutcome`, Employment-root Assignment-portfolio serialization, stable Assignment-root revision CAS, authenticated predecessor `AssignmentCapacitySettlement`, the published/versioned authenticated cross-context capacity/attempt API or event contract, epoch/purpose-bound signing-key authorization, owner/rollback epoch validation, Position-eligibility fencing, capacity-revision receipts, transaction-drained writer-fenced migration, pre-existing admission-sequence high-water capture, owner-local two-sided admission-close receipts, live-protocol quiescence before epoch retirement, transition-scoped obligation-bounded retirement reconciliation, durable epoch-transition arbitration, deterministic discrepancy manifest, two-service reconciliation, performance evidence, or rollback rehearsal.

## Requirement matrix

| Requirement | Current evidence | State |
|---|---|---|
| Keep Position in Organization and Assignment in People | `ARCHITECTURE.md`, `docs/TRD.md` | protected_architecture |
| Preserve durable Position identity/bitemporal versions and Assignment binding | ADR 0004 | protected_accepted |
| Preserve one Employment's visible Assignment allocation at `<= 1.0000` across distinct Assignments/Positions | ADR 0004 consequence plus ADR 0274 Employment-root serialization | proposed_design |
| Preserve retroactive correction across the complete currently authoritative effective-time domain | protected `docs/TRD.md` retroactive-correction rule plus ADR 0274 cutover scope | proposed_design |
| Preserve `active` or `open` Position coverage and visible seat allocation `<= 1.0000` | ADR 0005 | protected_accepted |
| Preserve union coverage when one Assignment interval spans multiple staffable Position versions | protected `validate_assignment_position_coverage` plus ADR 0274 `PositionEligibilityCoverage` | proposed_design |
| Record why synchronous availability/status-check-only is unsafe | PostgreSQL 18 §13.2 plus ADR 0274 alternative B | proposed_design |
| Define one canonical capacity/eligibility authority without cross-service SQL | ADR 0274 option C | proposed_design |
| Make `held` consume capacity but allow bounded autonomous expiry before commit fence | ADR 0274 capacity invariant/protocol | proposed_design |
| Make `commit_fenced` consume capacity without autonomous expiry | ADR 0274 protocol/failure semantics | proposed_design |
| Give every capacity-affecting Assignment mutation its own opaque `assignment_attempt_id` | ADR 0274 domain model/protocol | proposed_design |
| Bind reserve idempotency and semantic digest to exact attempt and authority context | ADR 0274 `reserve`/`arm_commit_fence` | proposed_design |
| Bind mutation digest to Employment portfolio, Assignment identity, operation, attempt, expected prior version, predecessor settlement, reservation evidence, result facts, and delta fences | ADR 0274 `AssignmentAttemptOutcome` | proposed_design |
| Serialize every allocation-changing Assignment mutation at the stable Employment root and re-read authoritative overlapping portfolio | ADR 0274 People aggregate/protocol | proposed_design |
| For existing Assignment mutation, lock Employment before Assignment and CAS the exact prior Assignment version | ADR 0274 `revise_assignment_capacity` | proposed_design |
| Block a successor capacity-affecting revision until Organization settlement is equivalent to the exact predecessor Assignment version | ADR 0274 `AssignmentCapacitySettlement` | proposed_design |
| Bind each terminal receipt to exact target reservation identity/version/digest and fence disposition | ADR 0274 terminal outcome/revision protocol | proposed_design |
| Authenticate durable cross-context receipts by canonical signature, issuer/audience, tenant, contract version, authority/rollback epoch, receipt identity, and exact target payload | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Bind each signing-key version to issuer, allowed authority/rollback epochs, and `domain_transition` versus `audit_only` purpose | ADR 0274 verification-key manifest | proposed_security_design |
| Preserve idempotent equivalent receipt replay while rejecting reused-ID/different-payload, retired-epoch, forged, wrong-audience, cross-tenant, or wrong-key-authority evidence | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Keep historical old-epoch receipts and keys verifiable for audit without restoring retired write authority | ADR 0274 authenticated receipt envelope | proposed_security_design |
| Make People commit Assignment mutation plus terminal `committed` evidence atomically | ADR 0274 People mutation protocol | proposed_design |
| Make stale-predecessor revision terminally non-committing so unused delta fences have exact release evidence | ADR 0274 revision protocol | proposed_design |
| Allow unresolved post-fence release only from authenticated terminal People `aborted` evidence that fences later commit | ADR 0274 terminalize/release semantics | proposed_design |
| Reject point-in-time Assignment absence/not-found as release authority | ADR 0274 failure/recovery semantics | proposed_design |
| Never shrink/release a confirmed debit from a mutable People read | ADR 0274 revision protocol | proposed_design |
| Fence positive capacity/eligibility deltas from exact settled predecessor backing before People commits increase, extension, or Position move | ADR 0274 revision protocol | proposed_design |
| Apply decrease/shortening/end only from authenticated terminal People committed revision evidence | ADR 0274 `apply_revision_receipt` | proposed_design |
| Emit settlement authority only after every disposition for the resulting Assignment version is applied and backing is equivalent | ADR 0274 `AssignmentCapacitySettlement` | proposed_design |
| Confirm target capacity before releasing source capacity on Position move | ADR 0274 revision failure/recovery semantics | proposed_design |
| Bind commit fence to normalized complete Position eligibility coverage | ADR 0274 capacity/eligibility invariant | proposed_design |
| Serialize eligibility-changing Position mutations against live fenced/confirmed debits at same Position root | ADR 0274 status-change protocol | proposed_design |
| Reject People-side mutable Position recheck as post-fence correctness mechanism | ADR 0274 protocol/failure semantics | proposed_design |
| Keep cross-context I/O outside Position-root, Employment-root, and Assignment-root transactions | ADR 0274 protocol/failure semantics | proposed_design |
| Apply terminal People receipts in new local Organization transactions | ADR 0274 confirm/release/revision protocol | proposed_design |
| Keep Person/Employment and unrelated PII out of Organization capacity evidence | ADR 0274 domain model | proposed_design |
| Prevent dual Position/capacity writers during extraction | ADR 0274 cutover/rollback | proposed_design |
| Drain every pre-fence legacy mutation before initial migration snapshot | ADR 0274 initial cutover barrier | proposed_design |
| Deterministically map every current legacy Assignment, including wholly past-effective occupancy, to confirmed reservation/terminal committed evidence | ADR 0274 cutover manifest | proposed_design |
| Keep superseded recorded-history as provenance without duplicate live debits | ADR 0274 projection rule | proposed_design |
| Fail cutover instead of rewriting invalid/unrepresentable legacy truth | ADR 0274 discrepancy rule | proposed_design |
| Issue transaction admissions from pre-existing owner-local source-epoch sequences and capture each owner's high-water in that owner's own admission-close CAS | ADR 0274 `EpochAuthorityTransition` | proposed_recovery_design |
| Require authenticated Organization and People admission-closure receipts before treating two-sided business admission as closed; do not assume a cross-service atomic close | ADR 0274 two-sided closure barrier | proposed_recovery_design |
| Cover the inter-owner closure gap by the later-closing owner's captured high-water while rejecting new work immediately at the owner that already closed | ADR 0274 owner-local closure-gap rule | proposed_recovery_design |
| Drain every ordinary Organization receipt at/below the captured retiring-epoch high-water mark before recovery work, abort, manifest, snapshot, or activation | ADR 0274 Organization admission/drain rule | proposed_recovery_design |
| Drain every ordinary People receipt at/below the captured retiring-epoch high-water mark before recovery work, abort, manifest, snapshot, or activation | ADR 0274 People admission/drain rule | proposed_recovery_design |
| Do not require a transaction admitted before transition creation or during the other owner's close gap to retroactively carry transition identity/generation | ADR 0274 high-water barrier | proposed_recovery_design |
| Keep a separate transition/retry-generation-bound reconciliation lane after ordinary business admission closes | ADR 0274 retirement reconciliation rule | proposed_recovery_design |
| Restrict retirement reconciliation to fixed retiring-epoch obligations and forbid new reservation/fence/Assignment/Position business truth | ADR 0274 recovery work ledger | proposed_recovery_design |
| Close retirement-reconciliation admission, capture its high-water, and drain every recovery receipt before quiescence/snapshot | ADR 0274 reconciliation drain rule | proposed_recovery_design |
| Settle every retiring-epoch `commit_fenced` attempt to terminal People evidence and apply its exact capacity disposition before snapshot | ADR 0274 protocol-quiescence sequence | proposed_recovery_design |
| Apply pending retiring-epoch confirm/release/revision receipts until Organization confirmed capacity and People Assignment truth are equivalent | ADR 0274 protocol-quiescence manifest | proposed_recovery_design |
| Prove both owner closure receipts, zero unresolved fenced state, zero unapplied capacity-changing terminal outcomes, and no open recovery receipt before authority/rollback epoch rollover | ADR 0274 protocol-quiescence manifest | proposed_recovery_design |
| Serialize concurrent rollovers by expected source epoch-pair CAS so one transition lineage and one target writer win | ADR 0274 `EpochAuthorityTransition` activation | proposed_recovery_design |
| Permit `aborted` only after both owner closure receipts, captured ordinary owner drains, recovery drain, and capacity-changing settlement obligations are fully terminal/applied | ADR 0274 abort rule | proposed_recovery_design |
| Keep an `aborted` rollover bound to the same source-pair transition lineage; retry only by expected-version CAS to a fresh proof generation while source business admission stays closed | ADR 0274 aborted-transition retry rule | proposed_recovery_design |
| Keep prior retry-generation proof artifacts immutable but ineligible as proof for a later generation | ADR 0274 generation-scoped recovery evidence | proposed_recovery_design |
| Reject retired-epoch receipts for new writes only after protocol state has been settled, not as a substitute for settlement | ADR 0274 epoch transition | proposed_security_recovery_design |
| Preserve current People mutation behavior while prerequisites remain mutable | #64 owner path; no extraction source in this slice | active_owner_boundary |
| Preserve Organization hierarchy prerequisite delta before extraction | #96 -> #119 owner order | active_owner_boundary |
| Require buyer/scientific realism to use provenance-backed right-cleared data | ADR 0274 acceptance | proposed_evidence_boundary |

## Planned executable evidence

| Claim | Required evidence | State |
|---|---|---|
| Concurrent overlapping Position capacity cannot exceed `1.0000` | real two-service/PostgreSQL race | planned_red_green |
| Distinct creates on different Positions cannot make one Employment allocation exceed `1.0000` | Employment-root PostgreSQL race | planned_red_green |
| Delayed create versus terminal abort has one terminal People outcome | forced attempt-race acceptance | planned_red_green |
| Two revisions from same Assignment predecessor cannot both advance lineage | Employment-root + Assignment-root CAS race | planned_red_green |
| Successor revision cannot use a lagging Organization ledger before predecessor settlement | V1 decrease/V2 settlement delay/V3 increase race | planned_red_green |
| Stale-predecessor abort releases only exact unused delta fences | Assignment-root/capacity integration | planned_red_green |
| Duplicate/reordered revision receipt cannot affect wrong reservation version or later settled backing | receipt-version/disposition/settlement tests | planned_red_green |
| Same key with different attempt or digest fails closed | contract/integration tests | planned_red_green |
| Forged/wrong-audience/cross-tenant/retired-epoch/wrong-target receipts fail closed | cross-context security tests | planned_security |
| Historical/audit-only signing key cannot authorize a current-epoch domain transition even with a valid signature | key-epoch-purpose authorization tests | planned_security |
| Equivalent receipt replay is idempotent while same-ID/different-payload fails | security/idempotency tests | planned_security |
| Position close cannot invalidate eligibility while authentic fence can still commit | Position-status-vs-create race | planned_red_green |
| Multi-version Position coverage stays complete/fenced | Position-coverage acceptance | planned_red_green |
| Remote latency cannot extend local root-lock lifetime | lock/I/O instrumentation | planned_operability |
| Crash after People commit before Organization application cannot free required capacity | forced-crash interleaving | planned_red_green |
| Increase/extension fences only positive target deltas from settled predecessor backing before People commit | revision-capacity integration | planned_red_green |
| Move confirms target before source release | cross-Position revision tests | planned_red_green |
| Decrease/shortening/end cannot use current read as release authority | revision-receipt tests | planned_red_green |
| Pre-fence legacy transaction cannot commit after projection starts | cutover-barrier race | planned_recovery |
| Migration identity/digest replay is deterministic across full effective-time projection | migration/recovery rehearsal | planned_recovery |
| Retroactive correction sees migrated historical occupancy | historical correction acceptance | planned_recovery |
| Invalid legacy occupancy creates discrepancy evidence and no authority switch | migration failure rehearsal | planned_recovery |
| One transition lineage coordinates independently captured owner-local admission closures without a cross-service transaction | two-owner admission-close protocol race | planned_recovery |
| Work admitted by the later-closing owner during the inter-owner gap remains below its captured high-water and is drained | staggered owner-close race | planned_recovery |
| Retiring epoch cannot pass recovery-work freeze while either owner closure receipt is missing or any captured ordinary owner admission remains open | two-sided business-admission/drain race | planned_recovery |
| Closed business admission does not deadlock terminalization/settlement of already-captured work | bounded retirement-reconciliation liveness race | planned_recovery |
| Retirement reconciliation cannot create new capacity/Assignment work outside the fixed obligation ledger | recovery-lane negative security/correctness tests | planned_recovery |
| Reconciliation lane cannot commit after snapshot | recovery admission close/high-water/drain race | planned_recovery |
| Abort cannot escape a generation while an owner closure receipt is missing, an ordinary captured admission/recovery receipt is open, or a settlement obligation remains nonterminal | abort-versus-drain race | planned_recovery |
| Retiring epoch cannot switch while one `commit_fenced` attempt is unresolved | protocol-quiescence rollback race | planned_recovery |
| Delayed old-epoch business mutation cannot enter after its owner's captured admission high-water closes | protocol business-admission/drain race | planned_recovery |
| Concurrent rollovers from one epoch pair cannot activate two targets | epoch-transition CAS race | planned_recovery |
| Abort then retry cannot release source-pair ownership or create a second transition lineage | aborted-transition retry race | planned_recovery |
| Concurrent equivalent retries of one aborted transition open exactly one fresh retry generation | transition-generation CAS race | planned_recovery |
| Prior-generation proof artifacts cannot satisfy a later retry generation | generation-evidence isolation rehearsal | planned_recovery |
| Quiescence manifest proves both owner closure receipts, zero unresolved fences/unapplied terminal outcomes, no open recovery receipt, and cross-owner equivalence | recovery manifest rehearsal | planned_recovery |
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
| People pre-write | valid signed Organization receipt with exact current issuer/audience/tenant/epoch/attempt/target and key authorized for that epoch/write purpose | proceed to domain validation |
| People pre-write | forged/wrong-audience/cross-tenant/retired-epoch/mismatched target or wrong-key-authority | fail closed before Assignment mutation |
| any receipt consumer | equivalent replay of already accepted terminal result | same result idempotently |
| any receipt consumer | same receipt ID with different payload/attempt/target/epoch | contradictory evidence; fail closed |
| one Employment empty portfolio | concurrent distinct A/B creates `0.6000` each on different Positions | Employment-root serialization allows at most one commit; other attempt terminally conflicts |
| People attempt unresolved | create wins attempt + Employment-root serialization | Assignment + terminal `committed` atomically if portfolio remains `<= 1.0000` |
| People attempt unresolved | terminalization wins | terminal `aborted`; later mutation cannot commit |
| People attempt `aborted` | delayed/retried mutation | no Assignment commit |
| People attempt `committed` | delayed/retried terminalization | return committed; no release authority |
| `commit_fenced` | exact terminal committed receipt with `consumed` | Organization `confirmed` by expected-version CAS |
| exact Assignment version fully backed after all dispositions | Organization settlement | signed `AssignmentCapacitySettlement` binds exact version/backing digest |
| Assignment predecessor settlement missing/stale/mismatched | successor capacity-affecting revision request | fail closed before successor admission/fencing |
| `commit_fenced` | exact terminal aborted receipt with `unused_releasable` | Organization `released` by expected-version CAS |
| `commit_fenced` | current absence/not-found/timeout/missing event | no release; reconciliation only |
| Assignment V1 | concurrent revisions A2/A3 both expect V1 | Employment root then stable Assignment root/CAS permits at most one successor |
| stale-predecessor attempt | exact abort/conflict receipt | only exact `unused_releasable` targets may release |
| settled Assignment V2=`0.5000` | V3=`1.0000` same-Position increase | fence exact `0.5000` delta before People commit |
| People-committed V2=`0.5000`, Organization still reflects V1=`1.0000` | V3=`1.0000` request | block until exact V2 settlement; lagging ledger cannot imply zero delta |
| confirmed occupancy | Position move | target occupancy fenced before People commit |
| confirmed occupancy | decrease/shortening/end commits in People | old debit stays until terminal revision receipt applied; successor revision waits for settlement |
| committed Position move | authenticated target receipt | target confirmed before source release |
| confirmed debit | mutable People read says smaller/ended/absent | no shrink/release |
| Position has fenced/confirmed debit | status mutation removes staffable coverage | local fail-closed; no remote call under lock |
| historical/audit-only key | signs a new receipt claiming current authority epoch | signature may verify cryptographically; write authorization still fails key epoch/purpose binding |
| legacy writer open | initial cutover enters draining epoch | reject new legacy admission; captured high-water waits for all earlier transactions |
| epoch E authority active | first rollover request with exact expected `(E,R)` | create one source-pair transition lineage; each owner independently CAS-closes its E admission gate and captures its own high-water; transition cannot advance until both authenticated closure receipts exist |
| Organization E gate closed, People E gate still open | People business request arrives in close gap | request may be admitted, but its sequence must be at/below People’s later captured high-water and drain before recovery freeze; new Organization E admission is rejected |
| epoch E transaction admitted before transition or before its owner's local close | receipt source pair/sequence is below captured high-water | ordinary drain obligation despite having no transition identity/generation |
| epoch E Organization business protocol closed | later reservation/fence request | no E business-admission sequence; reject |
| epoch E People business protocol closed | later E receipt-authorized create/revise mutation | no E business-admission sequence; reject |
| both owner closure receipts durable and ordinary drains closed | derive retirement recovery work | fixed retiring-epoch obligation ledger; no new business subject may enter |
| ordinary E business protocol closed, unresolved listed attempt | transition-bound `terminalize_attempt` recovery admission | allowed only for exact work-ledger obligation; may produce terminal outcome but no Assignment create/revise |
| ordinary E business protocol closed, exact listed terminal receipt pending | transition-bound apply/confirm/release/settle recovery admission | allowed only by exact version/digest; may reduce ambiguity/over-reservation but cannot create new fence/business mutation |
| ordinary E business protocol closed | recovery request tries reserve/fence/create/revise/unrelated Position mutation | fail closed; recovery lane is not substitute business admission |
| E `held` after both business-admission drains | ordinary safe release/expiry through listed recovery obligation | settle to non-consuming state before rollover |
| E `commit_fenced` after both business-admission drains | terminalize/reconcile exact listed attempt | terminal committed/aborted outcome, then apply exact disposition |
| E terminal revision/confirm/release receipt pending | quiescence recovery settlement | apply by exact-version CAS before snapshot |
| recovery work ledger empty | close reconciliation admission and capture recovery high-water | no new recovery admission; drain every recovery receipt through captured mark before quiescence |
| reconciliation admission closed but captured recovery receipt nonterminal | attempted quiesce/abort/snapshot/activation | block transition until recovery receipt terminal and authoritative work ledger rechecks empty |
| retiring E missing an owner closure receipt, or still has unresolved fence, captured open ordinary/recovery admission receipt, or unapplied capacity-changing outcome | attempted manifest/snapshot/epoch increment | block transition |
| transition `draining`, owner closure receipt missing or captured ordinary/recovery receipt still nonterminal | attempted abort | fail closed; remain `draining` |
| transition `draining`, drains closed but capacity-changing outcome unapplied | attempted abort | fail closed; settle first |
| transition `draining` or `quiesced`, both owner closure receipts present, ordinary/recovery drains and settlement complete, no activation receipt, source `(E,R)` still current | governed abort with expected transition version | mark same transition lineage `aborted`; source business admission remains closed |
| transition `aborted` | equivalent retry with matching expected version/current source/target/digest | CAS same transition to `draining`, increment retry generation, recompute fresh reconciliation/drain proof from authoritative source ledgers/state |
| transition `aborted` | two equivalent concurrent retries | one CAS opens the next generation; loser observes same generation idempotently |
| transition `aborted` | different target/digest, stale source pair, activation receipt, missing/inconsistent owner closure receipt, or unresolved captured obligation | fail closed; do not create/re-purpose another transition lineage |
| prior aborted retry generation | old proof artifact offered as current retry proof | audit only; recompute current generation proof from source ledgers/state |
| transition `quiesced` at source `(E,R)` | two concurrent activation attempts | expected-version/source-pair CAS permits one activation and one target writer only |
| losing equivalent rollover | winning transition/activation already durable | observe same result idempotently |
| losing contradictory rollover | source pair/transition version no longer expected | fail closed or refresh authority; never activate second target |
| retired E | otherwise valid historical receipt arrives | audit/replay existing terminal result only; no new domain transition |
| cutover barrier closed | deterministic migration projection | full effective-time Assignment truth maps to stable confirmed reservation evidence |
| post-cutover historical slice | retroactive overlapping write | migrated historical debit participates; no capacity/coverage bypass |
| drained legacy snapshot invalid | migration validation | deterministic discrepancy evidence; no switch |

## Required failure interleavings

### Concurrent creates on different Positions for one Employment

1. Employment E has no visible Assignment allocation on the target interval.
2. Organization validly fences R1=`0.6000` on Position P1 for attempt A1 and R2=`0.6000` on distinct Position P2 for attempt A2; Position-local capacity does not force those requests to contend.
3. Run both People creates concurrently and hold each after it has verified its Organization receipt but before Employment portfolio validation.
4. Both must acquire the same stable Employment root before committing. The first winner re-reads the authoritative portfolio and may commit `0.6000` plus terminal outcome.
5. The loser acquires the Employment root afterward, re-reads `0.6000`, observes that its result would be `1.2000`, and records terminal non-committing conflict evidence rather than an Assignment.
6. Organization releases only the loser's exact unused fence from the authenticated terminal conflict receipt.

Passing requires visible allocation for E never to exceed `1.0000`, even though the Position reservations were on independent aggregate roots.

### Delayed create versus terminal abort

1. Organization creates and commit-fences reservation R for attempt A.
2. People `create_assignment(A, R)` is delayed or in flight.
3. Reconciliation attempts to resolve A.
4. A read returning no Assignment does not authorize release.
5. If `terminalize_attempt(A)` records `aborted`, delayed create cannot commit afterward.
6. If create commits first, it atomically records terminal `committed`; terminalization returns committed and Organization must not release R.

Passing requires exactly one terminal People outcome and no execution that frees capacity while a later commit remains possible.

### Concurrent revisions from one predecessor

1. Assignment V1 is authoritative and backed by exact Organization settlement S1 for confirmed reservation R1.
2. Prepare A2 and A3 independently, both bound to V1/R1/S1; each may obtain positive delta fences.
3. Run People transactions concurrently.
4. Stable Employment-root serialization followed by Assignment-root serialization lets at most one verify V1/S1 and commit a successor.
5. Loser sees stale V1/portfolio evidence and records terminal non-committing conflict evidence.
6. Deliver winner/loser receipts duplicated and out of order. Organization confirms only winner `consumed` fences and releases only loser `unused_releasable` fences at exact expected reservation versions.

Passing requires one lineage successor, no Employment over-allocation, no under-reserved committed revision, and no wrong-target capacity mutation.

### Predecessor settlement delay versus successor increase

1. V1=`1.0000` is authoritative and settled in Organization.
2. People commits V2=`0.5000`; deliberately delay Organization application so the ledger still carries V1's `1.0000` backing and no V2 `AssignmentCapacitySettlement` exists.
3. Request V3=`1.0000` before V2 settlement. The successor must not treat the lagging `1.0000` ledger debit as if it were V2 backing and infer zero delta; admission fails/awaits exact V2 settlement.
4. Apply V2's terminal receipt, reduce backing to exact `0.5000`, and publish settlement S2 bound to V2 and its backing digest.
5. Retry V3 against V2/S2. Organization must fence the positive `0.5000` delta before People commit.
6. After V3 settles, deliver duplicate or reordered V2 receipts. Exact reservation-version CAS and settlement binding must make them idempotent/no-op or fail closed; they cannot reduce V3 backing.

Passing requires no committed Assignment version to become under-reserved during sequential revisions with delayed receipt delivery.

### Authenticated receipt rejection, replay, and signing-key authority

1. Create a valid current-epoch Organization fence receipt for tenant T, People audience, attempt A, reservation R@V, semantic digest D, signed by key K authorized for the claimed issuer/current `(authority_epoch, rollback_epoch)` and `domain_transition` purpose.
2. Verify it and replay the equivalent receipt; replay yields the same result.
3. Mutate signature, issuer, audience, tenant, attempt, target version, coverage digest, semantic digest, contract version, or epoch without valid authority; every variant fails before write.
4. Present a correctly signed receipt from a retired epoch; it cannot authorize a new transition.
5. Reuse one receipt ID with a different canonical payload; fail as contradictory replay.
6. Keep an old verification key Kold available for historical audit, mark it `audit_only` or outside the current epoch authorization range, and use Kold to sign a new payload that falsely claims the current epoch. The cryptographic signature may verify, but key-epoch-purpose authorization must fail before mutation.
7. Repeat symmetrically for People terminal receipts consumed by Organization.

Historical signature verification is audit evidence, not revival of retired write authority.

### Confirmed revision versus capacity adjustment

1. V1 is backed by confirmed R1 and exact settlement S1.
2. Start A2 bound to V1/R1/S1.
3. Fence positive delta R2 before any increase/extension/move can commit.
4. People CASes V1 and atomically commits V2 plus terminal outcome.
5. Crash before Organization application; R1 stays confirmed and R2 stays fenced; no capacity-affecting V3 can be admitted without V2 settlement.
6. Recovery confirms R2 before reducing/releasing superseded R1 slices and then publishes V2 settlement.
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

1. Hold one admitted legacy Position/Assignment transaction open with a pre-existing cutover admission sequence.
2. Atomically close durable legacy admission and capture its high-water mark.
3. Reject later legacy mutation admission.
4. Snapshot remains blocked until every receipt at/below the captured mark commits/rolls back.
5. Project the complete current effective-time truth twice; identities/digests/manifests are identical.
6. Validate all source facts losslessly before enabling Organization authority.

Passing requires an explicit transaction linearization barrier, deterministic projection, and no legacy commit after the snapshot.

### Live epoch retirement versus staggered owner admission closure

This RED verifies that transition creation neither requires retroactive receipt binding nor invents a cross-service atomic transaction.

1. Under source authority pair `(E,R)`, admit Organization transaction O and People transaction P before any transition exists. Their durable receipts contain `(E,R)` and owner-local monotonic admission sequences, but no transition identity/generation.
2. Hold O and P open. Start two rollover controllers from the same expected `(E,R)` pair. Exactly one source-pair transition-lineage CAS wins and records immutable target intent; no owner admission gate has to be changed in that transition transaction.
3. Close Organization E admission by Organization-local CAS, capture `organization_admission_high_water >= O.sequence`, and publish authenticated Organization closure receipt bound to T/G/(E,R). Do not close People yet.
4. During this deliberate gap, submit another People business mutation P2. It may still obtain a valid E People admission sequence because People owns that gate. A new Organization E request must already be rejected.
5. Now close People E admission by People-local CAS, capture `people_admission_high_water >= max(P.sequence, P2.sequence)`, and publish the corresponding authenticated People closure receipt. Verify later People E business admission is rejected.
6. Attempt recovery-work freeze, abort, manifest, snapshot, and activation before both closure receipts exist or while O, P, or P2 is nonterminal. Every attempt must stay blocked.
7. Let O, P, and P2 commit or roll back. Any committed E state becomes visible before the bounded recovery work ledger is frozen. Recompute generation-scoped drain proof from both authoritative admission ledgers and continue only after both captured sets are terminal.

Passing requires one transition lineage plus two owner-local closure linearization points: no distributed-ACID claim, no lost mutation in the inter-owner gap, no retroactive transition metadata, and no ordinary E mutation after the authoritative snapshot.

### Closed business admission versus retirement reconciliation

This RED verifies that fencing new E business work does not make old E obligations impossible to settle.

1. Under E, create and commit-fence reservation R for unresolved attempt A. End the Organization transaction; do not terminalize A.
2. Start retirement, acquire transition T, close Organization and People E business admission independently by owner-local CAS, capture both ordinary high-water marks, require both authenticated closure receipts, and drain all receipts through those marks.
3. Demonstrate that a new E reserve, fence, create, revise, or unrelated Position mutation cannot obtain ordinary business admission.
4. Derive transition T generation G recovery work ledger containing the exact R/A obligation. Attempt `terminalize_attempt(A)` through the closed ordinary People lane; it must be rejected. Admit the same exact obligation through T/G's reconciliation lane; it may produce only terminal `committed` or `aborted` evidence for A, never a new Assignment mutation attempt.
5. Admit the exact resulting receipt application to Organization through the same T/G reconciliation lane. It may confirm/release/settle only R at the expected version/digest; attempts to reserve capacity, arm a new fence, or touch an unrelated reservation fail closed.
6. Hold one recovery transaction open. Close reconciliation admission and capture `reconciliation_admission_high_water`. Manifest, quiesce, abort, snapshot, and activation must remain blocked until that recovery receipt is terminal.
7. After every recovery receipt through the captured mark is terminal, re-read authoritative E state. If the fixed subject set still has an unresolved next step, reopen reconciliation in the same generation, execute it, and repeat the close/high-water/drain cycle. When the work ledger is exhausted, close/drain once more and keep it closed.
8. Verify zero unresolved `commit_fenced` debits, zero unapplied capacity-changing outcomes, no open recovery receipt, and Organization/People equivalence before binding the quiescence manifest.

Passing requires both liveness and safety: old captured E work can be settled after ordinary admission closes, but the recovery lane cannot become a back door for new E business work or leave an after-snapshot recovery commit.

### Concurrent epoch rollover arbitration

1. Start with one active authority pair `(E,R)` and no transition.
2. Race controller A targeting writer W1 and controller B targeting W2, both using the exact expected source pair. One durable source-pair CAS/uniqueness boundary creates the transition lineage and immutable target intent only; it does not atomically mutate both owner databases.
3. Exactly one `EpochAuthorityTransition` becomes active. If both requests are byte-equivalent for the same target/digest, the loser observes the winner idempotently. If targets/digests differ, the loser fails closed or refreshes from current authority; it cannot create a second transition.
4. Independently close Organization and People E admissions under their owner-local gate CASes and attach both authenticated closure receipts/high-water marks to the winning transition. Any work admitted by the later-closing owner is included in that owner's captured mark. Drain both captured ordinary sets, settle protocol state through the bounded reconciliation lane, close/drain that lane, and bind one quiescence-manifest digest to the winning transition by expected transition-version CAS.
5. Race activation/retry again. Activation CASes both the transition version and still-current source `(E,R)` pair and atomically publishes the target authority pair plus immutable activation receipt.
6. Verify exactly one transition is `activated`, exactly one target writer accepts new mutations, the losing target never becomes authoritative, and stale retries from `(E,R)` cannot activate after the winner.

Passing requires one source epoch pair, one transition lineage, two authenticated owner-local admission-closure receipts, one activation receipt, and one target writer under all duplicate/reordered concurrent rollover attempts.

### Abort while admission is nonterminal, then retry

1. Start from source `(E,R)`, create transition T generation G, close both owner admissions independently with authenticated owner-local closure receipts/high-water marks, and leave one captured ordinary receipt nonterminal.
2. Attempt expected-version CAS to `aborted`. It must fail closed and T remains `draining`; source business admission remains closed.
3. Make both captured ordinary owner sets terminal, open bounded reconciliation, and deliberately leave one recovery receipt nonterminal or one capacity-changing terminal outcome unapplied in Organization. Abort must still fail closed.
4. Close/drain reconciliation and apply every capacity-changing obligation. Now, before activation, an expected-version abort may mark the same lineage `aborted` while `(E,R)` remains current and no activation receipt exists.
5. Preserve generation-G ordinary/recovery receipts, closure receipts, discrepancy/work-ledger/manifests as immutable history. Race two byte-equivalent retries against exact aborted T. One CAS increments retry generation to G+1; the loser observes the same winner.
6. G+1 does not reopen either E business-admission gate and does not treat G's proof artifact as its own. It freshly derives/recomputes reconciliation, drain, settlement, and quiescence proof from authoritative source ledgers/state through the already-closed source boundary.
7. Submit conflicting target/digest, stale-source, activation-present, missing/inconsistent closure-receipt, or unresolved-obligation retries; all fail closed without a second lineage.
8. Complete G+1 and verify exactly one activation receipt/target writer.

Passing requires abort never to shed a live ordinary or recovery mutation obligation, retry never to create source-pair ABA, and one source pair to retain one transition lineage across generations.

### Live epoch retirement versus unresolved fenced attempt

This is the RED that distinguishes protocol quiescence from ordinary database transaction drain.

1. Under epoch E, Organization creates and commit-fences R for attempt A; Organization transaction ends. People has not yet made A terminal.
2. Start rollback/epoch retirement by acquiring the exact source-pair transition, then close Organization and People E business admissions through separate owner-local CAS/high-water transactions. The transition must collect both authenticated closure receipts before treating ordinary admission as fenced.
3. Intentionally delay one E create so it arrives after Organization has closed but before People closes, and hold another already-admitted E People transaction. If the delayed create obtains People admission before the People-local close, its sequence must be captured by People’s high-water; if it arrives after that close, it must be rejected. Either way it cannot escape the drain boundary.
4. The captured People transactions keep the ordinary drain barrier open until they commit or roll back. Missing either owner closure receipt also blocks recovery freeze, snapshot, abort, and activation.
5. After both owner closure receipts exist and both captured ordinary admission drains close, derive the bounded reconciliation work ledger. Reconcile A through the transition-scoped lane. `terminalize_attempt(A)` may safely establish `aborted` if no admitted create committed, or it returns `committed` if one did. Exactly one terminal outcome exists.
6. Apply A's exact terminal receipt to Organization through transition-scoped reconciliation. Repeat for every listed E fence and pending E capacity-changing terminal obligation; do not admit new reserve/fence/create/revise work.
7. Close recovery admission, capture its high-water, and attempt abort, rollback snapshot, or epoch increment while any captured ordinary/recovery receipt is nonterminal, any E `commit_fenced` debit remains, or any E capacity-changing terminal outcome is unapplied. Every attempt must fail closed.
8. Build a deterministic quiescence manifest and prove both authenticated owner closure receipts, both captured-admission drains closed, recovery admission closed/drained, recovery work ledger exhausted, zero unresolved E `commit_fenced` debits, zero unapplied capacity-changing E outcomes, and equivalence between Organization confirmed occupancy and authoritative People Assignment truth.
9. Only now bind the manifest to the winning transition, take the authoritative rollback snapshot, project the chosen target writer, and activate by expected transition/source-pair CAS.
10. Deliver an otherwise authentic E receipt after rollover. It may support audit or replay of an already-durable terminal result but cannot authorize a new Assignment or capacity transition.

Passing requires no fictitious cross-service admission-close transaction, no after-snapshot old-epoch business or recovery mutation, no orphaned old-epoch debit/attempt, and no second target authority. Rejecting E receipts is the final authority boundary, not a substitute for pre-switch settlement.

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
