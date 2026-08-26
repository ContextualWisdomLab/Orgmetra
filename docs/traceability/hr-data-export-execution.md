# HR data export execution traceability

Status: active stacked PR evidence. This document describes `feat/hr-data-export-execution`; it is not protected-`develop` truth and does not authorize export, merge, deployment, or release.

## Scope and ownership

The parent review-control lane #75 owns `HrDataExportReviewPacket` and deliberately ends at `not_authorized_to_export`. This child owns the later one-time export execution boundary. It must remain dependency-first until #75 integrates, then retarget to fresh `develop` and reacquire every applicable exact-head gate. Parent checks and reviews do not transfer.

Orgmetra owns orchestration and value-minimized evidence only. Host adapters own authoritative export authorization, exact protected-field materialization, immutable audit/outbox persistence, and authenticated one-time delivery. No foreign CWL repository or cross-service application table is written by this boundary.

## Governed flow

1. Snapshot the exact reviewed export evidence and SHA-256 digest before authority work.
2. Freshly resolve export-specific authority, human approval, retention, legal-hold, tenant/resource/field/format/destination scope, and the half-open authorization window.
3. Reject any review-evidence drift observed across authority resolution before protected materialization.
4. Materialize only the exact reviewed fields under the 10 MiB artifact budget and verify media/field scope.
5. Recheck authorization freshness after protected materialization.
6. Commit value-minimized immutable audit evidence before bytes reach the egress port.
7. Recheck authorization freshness immediately before egress.
8. Publish only through the host-owned authenticated one-time-download port.
9. Validate the returned egress receipt against tenant, execution correlation, artifact digest/length, audit reference, destination, one-time-use state, and chronology.
10. Emit only value-minimized successful execution evidence; raw HR values never enter the durable execution receipt.

## Authorization-window semantics

The current active-PR repair separates delivery time from later receipt observation. A one-time delivery is valid only when its host receipt proves delivery within the reviewed authorization window. Later observation after expiry does not by itself make an already-completed in-window delivery retryable. Delivery at or beyond the half-open expiry boundary fails closed.

The egress port is the owner of the concrete side effect and delivery instant. Receipt-validation failure after that external side effect is therefore not permission to publish a second download. Recovery must preserve the same `export_execution_reference`/audit correlation and treat the prior delivery as requiring authoritative reconciliation rather than inventing a fresh export authorization or silently retrying egress.

## Evidence minimization

Durable execution evidence may contain correlation references, policy/evidence digests, artifact SHA-256 and byte length, controlled destination/state codes, audit correlation, and detached UTC chronology. It must not contain document/HR payload bytes, names, email addresses, compensation, ratings, free-form request text, credentials, tokens, or LLM output.

## Verification requirements

Current child evidence is non-passing until an exact-current-head `HR Data Export Quality` run materializes. The parent workflow previously accepted only `develop`, which prevented stacked child PRs targeting `feat/governed-hr-data-export-control` from receiving the focused gate. Parent #75 now carries a test-first workflow-materialization repair; this child commit intentionally synchronizes after that repair so GitHub can evaluate the base-branch trigger on the current child head.

Before any readiness transition require fresh exact-head focused coverage plus all applicable Foundation, Recovery, SAST, Security, central review, and stack/base evidence. Queued, absent, cancelled, stale, predecessor, status-only, or model-only evidence is non-passing.

## Trace links

- Parent review control: PR #75
- Execution implementation: PR #120
- Parent stacked-workflow regression: `01f8891d31aa1760eade861e2ed6ac849070d514`
- Parent stacked-workflow root repair: `18b7b08ba12c7cfb4c29193f98f4c106e25089af`
- Post-egress authorization-window regression: `3361d9e4dcbfaa63381ce93507b513792ed0ab45`
- Post-egress authorization-window root repair: `9f6b70c29e0f23d5684313dccf04833716afed39`
- Receipt/timestamp and review-drift hardening current predecessor: `33ef7e7929f29c16d55bcfd93e5907d79e21e048`
- Repository governance/control-plane gap: issue #89
