# HR Workspace Job grade review state traceability

## Truth boundary

- Protected `develop` truth remains `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` for this stack's base history; this child is **active-PR evidence only** until its dependencies are integrated.
- Parent UI contract: PR #130 `feat/hr-workspace-protected-read-state@b3b30058a79174000919d566fbbb1fdad80c62bf` owns shared protected-read accessibility semantics and Figma/Storybook correlation.
- Job grade governance owner: PR #101 owns `JobGradeDesignReviewPacket`; this UI does not import that unmerged package and does not claim its review is protected-branch runtime.
- Durable Job grade persistence is separately owned by dependency-first PR #109. This UI neither writes those tables nor treats persistence evidence as integrated.

## Buyer-visible requirement → evidence

| Requirement | Active-PR evidence | Safety meaning |
| --- | --- | --- |
| Load governed Job/Job Analysis/grade-design evidence before review | `loading` → `review` state model and Storybook stories | No cached or locally invented grade truth is treated as authoritative. |
| Human review remains distinct from compensation/employment authority | `review` and `recorded` messages explicitly deny compensation/employment-decision authority | Reviewing a Job grade design does not authorize pay, promotion, assignment, selection, or another employment action. |
| Prevent duplicate review submission while immutable evidence is being recorded | `recording` has `aria-busy=true` and a disabled action | One in-flight review recording is visible and duplicate activation is blocked in the interaction model. |
| Stale upstream evidence fails closed | `stale` is an assertive alert with a reload action | A changed Job/Job Analysis/grade-design context must be reloaded before another review. |
| Denied purpose/reviewer authority fails closed | `denied` is an assertive alert | The UI does not silently downgrade to a local or cached review path. |
| Service failure provides a safe next action | `error` is an assertive alert and explicitly rejects cached review evidence | Customer-facing copy guides recovery without fabricating governance evidence. |
| Storybook and Figma correlation remain discoverable | Every rendered state carries `data-figma-node-id="1:64"`; Storybook exposes eight named states | Reviewers can inspect loading, read-only, permission-denied, validation-error, error, and focus-related UI evidence. |
| Owned interaction logic has exact coverage | `.github/workflows/hr-workspace-job-grade-review-state.yml` runs Node 24 test coverage at 100% lines/branches/functions | No missing owned branch is accepted as complete evidence. |

## Data minimization

The state model carries only constant governed copy and interaction semantics. It does **not** accept or serialize Person/candidate identity, employee names, contact data, compensation or salary values, ratings, assessment results, credentials/tokens, prompts, or model output.

## Integration discipline

Keep this PR Draft while #53 and #130 remain unintegrated. After those dependencies merge, retarget this child to fresh `develop`, reconcile intervening HR Workspace changes, and rerun all applicable browser/accessibility/Foundation/SAST/Security/Recovery and central exact-head gates. No predecessor check, review, or focused stack-local GREEN result transfers across that retarget.
