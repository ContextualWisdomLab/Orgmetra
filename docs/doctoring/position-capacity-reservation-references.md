# Position capacity-reservation references

Checked against primary publisher documentation on 2026-09-08 (Asia/Seoul). These sources inform the Proposed architecture in ADR 0274; they do not prove the distributed protocol correct, imply certification, or substitute for executable concurrency/failure evidence.

## APA 7 references

Garcia-Molina, H., & Salem, K. (1987). Sagas. In *Proceedings of the 1987 ACM SIGMOD International Conference on Management of Data* (pp. 249–259). Association for Computing Machinery. https://doi.org/10.1145/38713.38742

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 13.2. Transaction isolation*. https://www.postgresql.org/docs/18/transaction-iso.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 13.3. Explicit locking*. https://www.postgresql.org/docs/18/explicit-locking.html

## Version and bibliographic notes

- PostgreSQL 18 is the current supported major documentation line checked on 2026-09-08 (Asia/Seoul); the PostgreSQL documentation surface announces PostgreSQL 18.6 as released on 2026-08-13. ADR 0274 uses the documented semantics, not a patch-specific behavior claim.
- PostgreSQL documents `READ COMMITTED` as its default isolation level and states that two successive commands in one transaction may see different committed data. That is why a separate availability, Position-status, or later Assignment-state read cannot be the authority for a different transaction's capacity mutation.
- PostgreSQL documents `SELECT ... FOR UPDATE` row locking as blocking competing writers/lockers until transaction end. That supports Position-root serialization inside the canonical Organization owner for reservation debits, eligibility-changing mutations, and evidence-bound capacity adjustments. It also means a network call made while that transaction is open would extend the local lock lifetime until the remote operation returns; ADR 0274 therefore keeps People/network I/O outside Position-root transactions.
- The canonical SIGMOD conference-paper record for Garcia-Molina and Salem is DOI `10.1145/38713.38742`. ACM also exposes a SIGMOD Record representation with DOI `10.1145/38714.38742`; ADR 0274 cites the conference-paper DOI to avoid treating the two identifiers as interchangeable.
- Garcia-Molina and Salem define a saga as a sequence of transactions whose partial execution is amended by compensating transactions when the whole sequence cannot complete. ADR 0274 uses that as a design vocabulary for explicit compensation. It does not infer that a timeout, retry, absent message, point-in-time missing record, later status read, or current Assignment projection proves that another transaction cannot commit or that confirmed capacity is safe to release.

## Design mapping

| Design choice | Primary evidence | Repository consequence |
|---|---|---|
| Reject `availability/status read -> separate Assignment write` as a correctness mechanism | PostgreSQL 18, §13.2 | Capacity and Position eligibility must be durably fenced under one canonical Organization authority before People commits Assignment. |
| Reject `current Assignment read -> confirmed capacity release` as a correctness mechanism | PostgreSQL 18, §13.2 plus Saga compensation vocabulary | Capacity-decreasing correction/end is applied only from terminal People mutation evidence bound to exact prior Assignment/reservation versions; a stale or point-in-time read cannot shrink an Organization debit. |
| Fence positive revision deltas before People commits larger occupancy | PostgreSQL 18, §13.2 plus Orgmetra seat invariant | Allocation increases and interval extensions fence only their positive Position/time-slice delta; Position moves fence target occupancy. Failures may temporarily over-reserve but cannot under-reserve the committed Assignment. |
| Serialize competing capacity debits and eligibility-changing Position mutations at the stable Position root | PostgreSQL 18, §13.3 | `organization_core` owns the local lock/transaction boundary for Position capacity and status/version eligibility; People does not query Organization application tables as correctness authority. |
| Keep remote coordination outside the Position row-lock transaction | PostgreSQL 18, §13.3 | A conflicting Organization mutation fails closed locally, then People terminalization/correction happens after that transaction ends; durable receipts are applied in later local Organization transactions. This avoids treating a database row lock as a distributed/network lock. |
| Model partial failure with explicit, auditable compensation/reconciliation | Garcia-Molina & Salem (1987) | `held`, `commit_fenced`, `confirmed`, terminal People attempt outcomes, and evidence-backed confirm/release/revision transitions are domain state, not transport heuristics. |
| Keep a post-fence debit and eligibility promise until terminal People evidence exists | Saga compensation vocabulary plus Orgmetra's fail-closed seat/status invariants | TTL/HTTP timeout/missing event/current `not found` cannot release `commit_fenced`; a confirmed debit likewise cannot be reduced from current-state reads. Exact terminal attempt/revision receipts determine idempotent confirm, release, or adjustment. |
| Confirm target capacity before releasing source on a Position move | Saga compensation vocabulary plus Orgmetra's single-writer/capacity invariant | Cross-Position correction may temporarily reserve both Positions, but recovery never exposes the moved Assignment without target capacity/eligibility or requires a distributed database lock. |

## Evidence boundary

The sources above justify why the repository must explicitly control concurrency, lock lifetime, and compensation. They do not establish that ADR 0274's provisional choreography, People-owned attempt fence, Position-eligibility fence, revision-receipt protocol, or migration barrier is safe. Acceptance requires real two-service/PostgreSQL interleavings, delayed-create-versus-terminal-abort and fenced-create-versus-Position-status-change races, increase/extension/move/decrease/end crash windows, stale/duplicate/out-of-order revision receipts, instrumentation proving remote latency cannot extend Position row-lock lifetime, transaction-drained cutover tests, deterministic migration replay, idempotent replay tests, migration/rollback evidence, and exact-head quality/security/review gates listed in ADR 0274.
