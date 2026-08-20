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
values, and English/Korean labels. It is fixture mode: it does not claim a
connected API or a deployed Storybook runtime. A full Storybook runner is
deferred until a second workspace justifies extracting shared components.
