# HR Workspace protected-read state traceability

## Status

Active stacked PR evidence only. This file does not claim integration into `develop` and does not create a new service API.

## Buyer problem

The parent HR Workspace already exposes purpose-bound protected People and Job Analysis reads. Its Figma baseline also requires loading, disabled, error, read-only, focus and validation states. A protected read must therefore make in-flight work perceivable and prevent an accidental duplicate request while still telling the user what to do after a denial or transport failure.

## Design authority

The existing Figma `Orgmetra Baseline` file `xu1ZK1zmtFcDep95R8oE9O`, Storybook Inventory node `1:64`, requires `default / hover / focus / disabled / loading / validation-error / read-only / high-risk-confirmation` states. This slice does not add or reinterpret application geometry. It turns the existing protected-read state requirement into executable Storybook evidence.

## Contract

`protectedReadViewModel()` accepts only exact built-in state strings and returns value-minimized interaction semantics. The `loading` state exposes `aria-busy="true"` and disables the submit control so one in-flight protected read cannot be duplicated from the Storybook interaction. Loaded evidence remains explicitly read-only. Denied and error states use alert semantics and include a concrete next action. No protected HR value, credential, bearer token, compensation value, rating, candidate value, or free-form note enters the state evidence.

The Storybook proof uses the shared Orgmetra design tokens and preserves an explicit `:focus-visible` treatment. It is design/interaction evidence, not authority to mutate People, Job Analysis, or any dedicated-writer dependency.

## Verification

The dedicated exact-head workflow runs `tests/hr-workspace-protected-read-state.test.mjs` directly on Node 24, proves exact candidate checkout, and requires a clean checkout. Parent #53 checks and reviews never transfer to this child. After #53 integrates, retarget this child to fresh `develop` and rerun every applicable local and central gate on the resulting exact head.
