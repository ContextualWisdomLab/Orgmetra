# HR Workspace Employment absence state traceability

Status: **active stacked PR**. This document records the presentation/interaction contract owned by this branch. It does not claim protected-`develop` availability, accessibility certification, leave approval, or authority to mutate Employment truth.

## Ownership boundary

- Parent presentation contract: #130 `feat/hr-workspace-protected-read-state@b3b30058a79174000919d566fbbb1fdad80c62bf`.
- HR Workspace product parent: #53.
- Reason-free bitemporal Employment absence truth: #113. This branch does not import or duplicate that unmerged HRIS-kernel implementation.
- Durable reason-free absence persistence: #114. This branch does not write its PostgreSQL relations or inherit its focused evidence.
- Employment leave review remains separately owned by #47. Absence truth must not be translated into leave reason, entitlement, schedule, benefit, compensation, fitness, or employment-decision authority.
- Figma correlation: `Orgmetra Baseline`, Storybook Inventory node `1:64`, freshly read on 2026-08-28. The node requires `default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation` as the shared inventory. This read-only absence slice uses the applicable default/loading/validation/read-only/focus states and deliberately does not invent a consequential confirmation action.

## Interaction contract

- `idle`: explain what fresh reason-free Employment absence evidence will be loaded and why cached evidence is insufficient.
- `loading`: mark the surface busy and disable duplicate requests while current business/system evidence is resolved.
- `absent`: read-only reason-free operational truth that the Employment is absent at the reviewed coordinate; no reason disclosure or consequential authority.
- `notAbsent`: read-only truth that no confirmed absence is visible at the reviewed coordinate; it must not be interpreted as attendance, availability, or fitness for work.
- `denied`: fail closed on purpose/authority denial and direct the user to correct authorization.
- `stale`: require a fresh authoritative Employment/absence read rather than relying on prior evidence.
- `blocked`: surface authoritative tenant/Employment/Person/status/version inconsistency and require that inconsistency to be resolved first.
- `error`: prohibit inference from cached/partial evidence and explain the safe retry prerequisite.

The interaction view model is constant and value-minimized. It carries no Person/Employment/Assignment identifier, worker name/contact data, absence or leave reason, medical/family/statutory/disciplinary/benefit fact, compensation/rating/assessment value, credential/token, prompt, or model output.

## Evidence and accessibility

The focused workflow executes the exact candidate under Node.js 24 and requires 100% line, branch, and function coverage for this interaction contract. Storybook reuses existing Orgmetra design/focus tokens and the existing Figma inventory rather than introducing a parallel design system. WCAG 2.2 and WAI-ARIA 1.2 primary final references are recorded under `docs/doctoring/hr-workspace-employment-absence-accessibility-references.md`.

## Dependency-first integration

Keep this PR Draft and process #53 -> #130 first. The focused child gate is stack-local evidence only; #53/#130/#113/#114/#47 checks or reviews never transfer. After #130 actually integrates, retarget/revalidate this child against fresh `develop`, reconcile intervening HR Workspace/absence contracts, and rerun every applicable browser/accessibility/Foundation/Recovery/SAST/Security and central required workflow on one resulting exact head.

Do not self-approve, use routine administrator bypass, race another lifecycle writer, infer a reason or consequential HR authority from the read-only absence state, transfer predecessor evidence, or mutate a dedicated-writer dependency.
