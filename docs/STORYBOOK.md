# Storybook Contract

Design tokens live in `packages/design-tokens/` and map to the Figma file at https://www.figma.com/design/xu1ZK1zmtFcDep95R8oE9O. Repeating HR actions use one token each: approve, review, correct, request-evidence, compare, export, and escalate. Storybook stories must consume those tokens instead of one-off colors.

## Component inventory

- `HrActionButton` (tokenized approve/review/correct/request-evidence/compare/export/escalate)
- `Button`
- `LinkButton`
- `TextField`
- `SelectField`
- `DateRangeField`
- `EffectiveDateBadge`
- `StatusChip`
- `EvidenceCitation`
- `EvidenceDrawer`
- `DataTable`
- `Timeline`
- `OrgTreeNode`
- `PersonSummary`
- `PositionCard`
- `AssignmentSplit` (show exclusive-job and seat-over-1.0000 next actions)
- `DecisionRecord`
- `ValidationMetric`
- `ExactValueTable`
- `EmptyState`
- `ErrorState`
- `PermissionDenied`
- `AuditEvent`

## Required states

Each interactive component requires at least these stories where applicable:

- default
- hover
- focus-visible
- disabled
- loading
- read-only
- validation-error
- permission-denied
- high-risk-confirmation

## Accessibility contract

- All charts require exact-value tables.
- Every evidence citation opens a keyboard-accessible drawer.
- High-impact actions require preview, reason, actor, purpose, and confirmation.
- Missing evidence is shown as `unknown`, not `failed`.

## Local executable slice

`apps/hr-workspace/` is the first dependency-free executable slice of the
Employee Profile and HR Home experience. It consumes the shared CSS tokens,
keeps the Figma node IDs in the markup, and exercises evidence review,
purpose-bound permission denial, high-impact confirmation, exact allocation
values, and English/Korean labels. The Job Analysis and Employee Profile People
views are API-bound read surfaces: a host may inject an API base URL and
short-lived authorization provider through `globalThis.__ORGMETRA_JOB_ANALYSIS__`
and `globalThis.__ORGMETRA_PEOPLE__`. The fixture has no such provider and
therefore makes no connected-data claim or local-data fallback.

## Local Storybook runtime

The repository uses Storybook `10.5.10` with
`@storybook/web-components-vite` and native HTML/CSS stories in
`apps/hr-workspace/workspace.stories.js`. The stories cover tokenized action
states, read-only and validation-error fields, purpose-bound denial, the
keyboard-accessible evidence drawer, high-impact confirmation, and exact
assignment values. Shared design tokens and workspace CSS are imported by
`.storybook/preview.js`.

Run `npm run storybook` for the local development UI or
`npm run build-storybook` for the static build. This is local component and
state evidence; it does not replace connected People API or browser E2E
evidence. The Job Analysis and People read surfaces each require a real
protected API runtime before they can be called connected or released.
