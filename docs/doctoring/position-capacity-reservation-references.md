# Position capacity-reservation references

Checked against primary publisher documentation on 2026-09-08. These sources inform the Proposed architecture in ADR 0274; they do not prove the distributed protocol correct, imply certification, or substitute for executable concurrency/failure evidence.

## APA 7 references

Garcia-Molina, H., & Salem, K. (1987). Sagas. In *Proceedings of the 1987 ACM SIGMOD International Conference on Management of Data* (pp. 249–259). Association for Computing Machinery. https://doi.org/10.1145/38713.38742

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 13.2. Transaction isolation*. https://www.postgresql.org/docs/18/transaction-iso.html

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: 13.3. Explicit locking*. https://www.postgresql.org/docs/18/explicit-locking.html

## Version and bibliographic notes

- PostgreSQL 18 is the current supported major documentation line checked on 2026-09-08; the PostgreSQL documentation surface announces PostgreSQL 18.6 as released on 2026-08-13. ADR 0274 uses the documented semantics, not a patch-specific behavior claim.
- PostgreSQL documents `READ COMMITTED` as its default isolation level and states that two successive commands in one transaction may see different committed data. That is why a separate availability read cannot be the capacity authority for a later write.
- PostgreSQL documents `SELECT ... FOR UPDATE` row locking as blocking competing writers/lockers until transaction end. That supports Position-root serialization inside the canonical capacity owner, but does not make operations in two services one ACID transaction.
- The canonical SIGMOD conference-paper record for Garcia-Molina and Salem is DOI `10.1145/38713.38742`. ACM also exposes a SIGMOD Record representation with DOI `10.1145/38714.38742`; ADR 0274 cites the conference-paper DOI to avoid treating the two identifiers as interchangeable.
- Garcia-Molina and Salem define a saga as a sequence of transactions whose partial execution is amended by compensating transactions when the whole sequence cannot complete. ADR 0274 uses that as a design vocabulary for explicit compensation. It does not infer that a timeout, retry, or absent message is proof that a prior transaction did not commit.

## Design mapping

| Design choice | Primary evidence | Repository consequence |
|---|---|---|
| Reject `availability read -> separate Assignment write` as a correctness mechanism | PostgreSQL 18, §13.2 | Capacity must be durably consumed under one canonical Organization authority before People commits Assignment. |
| Serialize competing capacity debits at the stable Position root | PostgreSQL 18, §13.3 | `organization_core` owns the lock/transaction boundary for Position capacity; People does not query Organization application tables. |
| Model partial failure with explicit, auditable compensation/reconciliation | Garcia-Molina & Salem (1987) | `held`, `commit_fenced`, `confirmed`, and evidence-backed release/adjust transitions are domain state, not transport heuristics. |
| Keep a post-fence debit until authoritative outcome evidence exists | Saga failure semantics plus Orgmetra's fail-closed seat invariant | TTL may expire `held`; TTL/HTTP timeout/missing event cannot release `commit_fenced`. |

## Evidence boundary

The sources above justify why the repository must explicitly control concurrency and compensation. They do not establish that ADR 0274's provisional choreography is safe. Acceptance requires the real two-service/PostgreSQL interleavings, crash-window tests, idempotent replay tests, migration/rollback evidence, and exact-head quality/security/review gates listed in ADR 0274.