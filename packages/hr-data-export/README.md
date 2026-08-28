# Orgmetra HR Data Export Control

This package separates **pre-export human review** from the later **audited one-time export execution** boundary. Neither stage is blanket access: execution must freshly re-resolve export-specific authorization, exact tenant/resource/field scope, accountable human approval, retention/legal-hold state and authorization freshness before protected values are read.

## Pre-export review

`HrDataExportReviewPacket` binds one tenant, one opaque HR resource, one purpose-bound authorization evidence reference and SHA-256 digest, one explicit sorted/unique field subset, distinct requester/reviewer actors, one export format, one delivery class, one evidence version and one detached UTC instant. It carries no HR field values and remains `not_authorized_to_export`.

Creation-time canonical review evidence is sealed in a process-local weak registry outside packet-writable state so low-level valid-looking post-issuance rewrites cannot create a second reviewed truth. Packet equality is intentionally identity-based because the seal is instance-bound; compare canonical JSON or its SHA-256 digest for semantic equality. This is defense in depth only; durable uniqueness and replay/idempotency remain host persistence responsibilities.

## One-time execution

The stacked execution boundary `execute_reviewed_hr_export(...)` accepts the exact sealed review packet and follows one fail-closed order:

1. snapshot and hash the reviewed scope;
2. ask an authoritative host adapter for **fresh export-specific authorization**, policy state and human-approval evidence;
3. prove the review did not change across authority resolution and require the authority result to bind the exact reviewed tenant/resource/fields/format/destination;
4. reject expired/not-yet-valid authorization, retention blocks or legal-hold blocks **before** protected fields are materialized;
5. materialize only the reviewed field tuple into exact immutable bytes, with a hard 10 MiB budget and exact media type;
6. re-check authorization freshness after materialization;
7. commit a value-minimized immutable audit/outbox receipt that binds the review, export authorization, human approval and exact artifact SHA-256/byte length;
8. re-check authorization freshness after audit and **before** outbound egress;
9. call the host-owned `authenticated_one_time_download` publication operation exactly once for the execution correlation;
10. validate that the immediate delivery receipt proves `delivered_at` occurred inside the half-open authorization window and no later than Orgmetra's post-egress observation;
11. if publication raised after a possible side effect or the immediate receipt is unusable, call the host's **reconciliation-only** operation for that same execution/audit/artifact correlation; reconciliation may read existing delivery evidence but must never republish bytes;
12. issue a successful value-minimized execution receipt only from valid immediate or reconciled delivery evidence. If authoritative reconciliation is unavailable or invalid, raise `HrDataExportDeliveryIndeterminateError` with an explicit **do not republish automatically** contract.

A delivery that completed inside the authorization window remains a completed audited delivery even if Orgmetra observes its receipt after the window has subsequently expired. This prevents a successful one-time delivery from being reported as a retryable failure merely because receipt processing crossed the expiry boundary. Conversely, a receipt whose actual `delivered_at` is at or after authorization expiry fails closed.

A clock failure after the publication call is also an indeterminate delivery outcome, not a safe retry signal. Operators must reconcile the existing `export_execution_reference` and audit correlation before any later action. The governed function never invokes the publication operation twice in one execution attempt.

The final Orgmetra receipt stores correlation, digests, artifact size, audit/egress references and chronology only. It never contains employee names, email values, employee numbers, compensation, ratings, candidate data or raw exported content. Its creation-time canonical evidence is sealed outside receipt-writable state so post-issuance rewrites fail closed; receipt equality is likewise identity-based, so compare canonical JSON or its SHA-256 digest for semantic equality.

## What this package still does not own

The package does not implement Keyverse identity, direct foreign-service SQL, email/file-share destinations, cloud-object-store policy, legal entitlement determination, payroll/statutory accounting, or release/deployment authority. Host adapters must use published Orgmetra/service contracts and must not treat retrieval authorization as export authorization. Delivery credentials and raw audit-store implementation remain outside this value-minimized domain package.

The concrete egress host owns durable idempotency and lookup by `export_execution_reference`. Its `reconcile_one_time_download(...)` implementation is explicitly a read/reconciliation path over the existing one-time-delivery outcome, not a second delivery command. An indeterminate error therefore requires operator/host reconciliation, not automatic retry.

## Customer/operator next action

For a reviewed request, verify that the exact requested field list, reason, destination and accountable reviewer are still appropriate. The execution host must then obtain a fresh export-specific authority decision and human approval, materialize only that exact scope, durably audit before delivery, and stop immediately if scope, policy, legal hold, retention or authorization freshness changes before delivery. A one-time delivery host must record the actual delivery instant and support correlation-based reconciliation so an ambiguous response is resolved against the original delivery instead of creating a duplicate export.

## Verification

```bash
PYTHONPATH=packages/hr-data-export/src python -m pytest \
  -c packages/hr-data-export/pyproject.toml packages/hr-data-export/tests
```

`HR Data Export Quality` checks the exact candidate head, compiles source/tests, requires exact 100% owned statement/branch coverage, and verifies a clean checkout. Foundation, Recovery, SAST and Security remain independent evidence and must also be fresh for the exact integrated candidate.

## Status

The review root is active PR #75. The execution contract is a **dependency-first active stacked PR**, not protected-`develop` truth and not transferable merge evidence. #75 must integrate first; the child must then retarget to fresh `develop` and rerun all applicable gates without inheriting parent checks/reviews.
