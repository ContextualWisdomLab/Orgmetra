# HR Workspace document retrieval interaction-state traceability

## Status boundary

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` does not contain this workflow-specific UI state contract.
- **Parent active PR:** #130 owns the shared protected-read accessibility/Storybook state semantics and Figma correlation. This child reuses that interaction vocabulary rather than creating a second generic protected-read renderer.
- **Backend active PR:** #116 owns a separate purpose-bound HR document retrieval execution boundary. This UI child does not import that unmerged package and does not claim that a UI state is authorization.
- **This active PR:** adds only value-minimized HR document retrieval interaction evidence for authorization, bounded artifact verification, immutable audit-before-release, read-only handoff, denial, expiry, and transport/audit failure.

## Buyer-facing contract

| UI state | Meaning | Safe next action | Authority boundary |
| --- | --- | --- | --- |
| `idle` | No protected operation is in flight. | Confirm purpose/scope, then start one authorization request. | No read authority exists. |
| `authorizing` | Current tenant/document/purpose scope is being authorized. | Wait; duplicate retrieval is disabled. | No artifact read is implied. |
| `reading` | A bounded protected artifact read and SHA-256 verification is in flight. | Wait for verification. | UI does not receive or persist document bytes as state evidence. |
| `auditing` | Verified artifact is waiting for immutable access evidence. | Wait for the audit append. | Bytes are not considered releasable before durable audit succeeds. |
| `ready` | Verified, audited read is ready inside the authenticated HR session. | Open only in that authenticated session. | Read-only; not export or employment-decision authority. |
| `denied` | Purpose/requester/document/delivery scope was not authorized. | Review purpose and access scope before a new authorization attempt. | Fail closed. |
| `stale` | Authorization expired before release. | Start a new authorization request. | Expired decisions are never reused. |
| `error` | Protected source or audit boundary failed. | Check protected source/audit service; do not use cached data. | No local fallback. |

All rendered state evidence is constant application copy. It does not contain document bytes/text/title, names, email/phone data, compensation, ratings, credentials/tokens, model output, or another service's application-table values.

## Design and accessibility trace

The parent #130 maps existing Figma `Orgmetra Baseline` Storybook Inventory node `1:64` to executable loading, disabled, error, read-only and focus semantics. This child adds workflow-specific stories without changing that design authority. In-progress phases use `aria-busy=true` and disable duplicate submission; denial/expiry/error use assertive alert semantics; normal progress/read-only states use polite status semantics; keyboard focus remains visible through the existing Orgmetra focus-ring token.

## Verification

`tests/hr-workspace-document-retrieval-state.test.mjs` requires all eight states, value-minimized copy, safe next-action copy, exact runtime-state rejection, Figma correlation, Storybook inventory, visible-focus styling and exact 100% line/branch/function coverage through the dedicated workflow.

Stack-local GREEN never transfers to #130, #53, #116, or protected-main integration. After dependencies integrate, retarget/revalidate against fresh `develop` and rerun every applicable browser/accessibility/Foundation/SAST/Security/Recovery/central gate on one exact head.
