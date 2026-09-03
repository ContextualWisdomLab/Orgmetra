# Wireframes

The Figma baseline contains six role-based wireframes:

- HR Home
- Job Architecture
- Recruiting Workspace
- Employee Profile
- Validate
- Admin & Integrations

Figma file: https://www.figma.com/design/xu1ZK1zmtFcDep95R8oE9O

The Figma baseline was re-verified against the live `Orgmetra Baseline` page for this interaction slice. Figma nodes `1:10` (HR Home) and `1:28` (Employee Profile) remain the visual geometry baseline. The keyboard bypass control below is intentionally a focus-only interaction affordance rather than a persistent geometric change to those frames; its visible focus state is captured in Storybook and its behavior is enforced by browser tests.

## HR Home

Primary action cards:

- Review evidence
- Approve job profile
- Resolve effective-date conflict
- Open validation study

Keyboard interaction contract:

- The first keyboard-focusable control is **Skip to main content** / **본문으로 건너뛰기**.
- It becomes visibly rendered when focused and moves focus to the `main` landmark, bypassing repeated workspace navigation.
- The control follows the active English/Korean workspace locale and uses the shared focus-ring token.

## Job Architecture

Panels:

- Job version header
- Evidence source list
- Task inventory
- FJA coding panel
- KSAO linkage panel
- SME approval status

## Recruiting Workspace

Panels:

- Candidate pipeline
- Candidate evidence timeline
- Requirement match table
- Interview guide
- Selection decision record

## Employee Profile

Panels:

- Person summary
- Employment history
- Position and assignment history
- Exclusive-versus-concurrent employment badge with the next action when a second job overlaps
- Seat-capacity warning when visible allocations would exceed 1.0000
- Manager and organization timeline
- Performance criteria and observations

The same page-level keyboard bypass contract applies before the Employee Profile navigation path, so repeated sidebar navigation is not a prerequisite to reaching the profile content.

## Validate

Panels:

- Study registry
- Predictor and criterion versions
- Predictive validity chart
- Subgroup diagnostics
- Drift and invariance warnings
- Policy change recommendations

Every policy change recommendation card must display the immutable supporting evidence/version links, confidence or interval information when scientifically defined, explicit limitations and subgroup caveats, the accountable human reviewer, and the consequence of approval. Recommendations remain drafts until a human chooses one of these visible actions: **Review**, **Request more evidence**, **Approve**, or **Escalate**. Approval requires actor, purpose, reason, evidence versions, and a single-use confirmation reference; the UI never presents an LLM-generated recommendation as an autonomous employment decision.

## Admin & Integrations

Panels:

- Keyverse identity status
- CWL adapter health
- Purpose-bound access policy
- Audit and provenance events
- Migration job status
