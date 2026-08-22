# Governed outbox retry policy traceability

## Scope

This document distinguishes shipped repository truth from the active retry-policy change so buyer and diligence readers do not infer capabilities that are not yet on protected `develop`.

| Requirement | Evidence | Maturity |
| --- | --- | --- |
| Durable outbox attempts and dead-letter budget | migrations 0004–0008 on protected `develop` | implemented_on_protected_main |
| Caller-independent tenant/target retry delay | `0016_outbox_retry_policy.sql`, `test_outbox_retry_policy_postgres.sh` | implemented_on_active_pr |
| One active policy per tenant and delivery target | partial unique index plus adversarial PostgreSQL contract | implemented_on_active_pr |
| Tenant-isolated retry-policy evidence | FORCE RLS plus NOBYPASSRLS cross-tenant regression | implemented_on_active_pr |
| Fail-closed retry when no active policy exists | transition trigger and governed retry wrapper regression | implemented_on_active_pr |
| Capped exponential delay | deterministic calculation contract | implemented_on_active_pr |
| Jittered retry scheduling | not implemented by this PR | planned |
| Verified downstream delivery receipts | outside this PR; downstream contract evidence is still required | planned |

## Protected-main truth

Protected `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` contains durable lease, completion, retry-attempt-budget, escalation, and dead-letter primitives. Its legacy five-argument `retry_outbox_delivery(...)` accepts a caller-provided delay and protected truth has no durable tenant/target retry-policy relation.

## Parent-stack truth

PR #51 (`docs/protected-truth-refresh`) is the dependency parent for canonical buyer-truth and deterministic provenance reconciliation. PR #82 is intentionally stacked on that branch rather than competing with its canonical inventory edits.

## Active PR truth

PR #82 introduces `outbox_retry_policy_record`, a capped exponential delay calculator, a database transition guard that rejects caller-selected retry timing, and `retry_outbox_delivery_with_policy(...)`. A raw legacy retry call cannot bypass policy because the actual leased-to-pending state transition is checked at the database owner boundary.

The new delay policy does not replace the protected `maximum_attempt_count` budget. Attempt exhaustion remains governed by the existing durable delivery record; this PR governs only when a nonterminal retry may become eligible again.

The active PR does **not** claim that asynchronous delivery is fully production-ready. It does not add downstream receipt verification, transport-specific producer configuration, or jitter. Those remain separate release-readiness concerns.

## Verification

The dedicated PostgreSQL contract requires:

- exact tenant isolation under a non-BYPASSRLS reader role;
- deterministic capped delay sequence `2,4,8,8,8,8` for the fixture policy;
- rejection of a forged raw retry delay before state mutation;
- policy-version evidence returned by the governed retry wrapper;
- fail-closed behavior after the active policy is closed; and
- rejection of multiple simultaneously active policies for one tenant/target.

No dedicated-writer CWL dependency is modified by this lane.
