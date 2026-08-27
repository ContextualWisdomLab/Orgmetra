# HR Workspace one-time export delivery interaction traceability

## Status

Active PR only. This interaction evidence is not shipped default-branch product truth and is not an authorization or release artifact.

Technical dependency chain: #53 → #130 → this child. Semantic export-owner dependencies remain #75 (governed export review) and #120 (audited one-time delivery). Their checks, reviews, backend authority, and persistence evidence do not transfer into this UI branch.

## Buyer risk closed

A one-time HR export is a sensitive, consequential data-egress operation. The UI must not make review, delivery, retry, or reconciliation look interchangeable. This slice makes the next safe action explicit without embedding protected HR values or credentials in component-state evidence.

| State | Interaction evidence | Safe next action |
|---|---|---|
| `review` | Figma-required high-risk confirmation; delivery disabled | Confirm the reviewed purpose/scope/destination evidence |
| `ready` | UI confirmation complete; confirmation locked; delivery handoff enabled | Start one audited one-time delivery attempt; backend still revalidates authority |
| `publishing` | `aria-busy=true`; confirmation and delivery disabled | Wait; do not duplicate the send |
| `delivered` | Read-only terminal receipt state; delivery disabled | Review immutable receipt; do not republish |
| `indeterminate` | Assertive error state; delivery disabled | Do not send again; reconcile the existing delivery reference |
| `denied` | Assertive authorization-denied state; delivery disabled | Resolve purpose-bound authorization and begin a newly reviewed export only after approval |

## Privacy and authority boundary

`hr-export-delivery-state.js` accepts only the governed state name and emits constant copy. It does not accept HR values, Person/Employment identifiers, document content, destination addresses, credentials, tokens, compensation, ratings, or model output. Storybook evidence therefore cannot itself exfiltrate protected HR payloads.

The `ready` UI state is not delivery authorization. The authoritative export service must still re-resolve the exact reviewed export packet, tenant/purpose/field scope, authorization freshness, destination class, immutable audit/outbox correlation, and one-time publication semantics defined by the export owner boundaries. An ambiguous external outcome is reconciliation-only; the UI deliberately has no republish action in `indeterminate`.

## Accessibility / Product Design mapping

Figma `Orgmetra Baseline` node `1:64` requires high-risk confirmation, loading, disabled, read-only, error, and focus states. Parent #130 owns the shared pattern. This child reuses existing Orgmetra spacing/surface/action/focus tokens and adds only workflow-specific semantics. Focusable controls use the existing `--orgmetra-focus-ring`; busy/error status is conveyed programmatically rather than by color alone.

The dedicated Storybook states are `ReviewRequired`, `ConfirmedReady`, `Publishing`, `DeliveredReadOnly`, `DeliveryIndeterminate`, and `PermissionDenied`.

## Verification

`tests/hr-workspace-export-delivery-state.test.mjs` requires:

- high-risk confirmation before delivery;
- exactly one enabled delivery handoff state;
- duplicate confirmation/delivery prevention during publishing;
- no republish action after delivered or indeterminate outcomes;
- explicit customer next actions for denial and ambiguity;
- no protected-value vocabulary in state evidence;
- exact built-in state input semantics; and
- Storybook/Figma correlation, tokenized focus treatment, and exact 100% line/branch/function coverage in the dedicated workflow.

After the technical parent integrates, this child must be retargeted to fresh `develop`. Before representing the interaction as commercial product truth, also refetch the current #75/#120 export contracts and rerun every applicable browser/accessibility/Foundation/SAST/Security/Recovery/central workflow on the resulting exact head. Predecessor or parent evidence never transfers.
