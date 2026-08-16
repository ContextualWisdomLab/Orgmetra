# Wireframes

The Figma baseline contains six role-based wireframes:

- HR Home
- Job Architecture
- Recruiting Workspace
- Employee Profile
- Validate
- Admin & Integrations

Figma file: https://www.figma.com/design/xu1ZK1zmtFcDep95R8oE9O

## HR Home

Primary action cards:

- Review evidence
- Approve job profile
- Resolve effective-date conflict
- Open validation study

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
