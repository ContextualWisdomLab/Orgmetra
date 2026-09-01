# HR Workspace Job Architecture traceability

Status: **active Draft PR evidence only**. Nothing in this document turns #147 into protected-`develop` truth, merge authorization, or authoritative Job mutation capability.

## Dependency and ownership boundary

- Parent interaction owner: #130 `feat/hr-workspace-protected-read-state@68896baa692ecf6fec8f21cfe5d981440be6071c`.
- Merged Job Analysis evidence owner: #25.
- Merged Job Analysis snapshot persistence/read owner: #38.
- Active model-assisted Task/FJA/KSAO draft owner: #117; raw model output remains untrusted draft evidence.
- Active Job-grade review/persistence owners: #101 → #109.
- This PR #147 owns only the Job Architecture workspace presentation/interaction state model, tokenized styling, Storybook stories, focused accessibility/privacy regression, and this traceability evidence.

No parent/backend checks or reviews transfer into this child. This child does not create a shadow Job Analysis, Job-grade, Position, Assignment, candidate, compensation, or employment-decision authority.

## Product-design correlation

Fresh Figma `Orgmetra Baseline` evidence on 2026-08-28 identifies Job Architecture node `1:16` and Storybook Inventory node `1:64`. The executable markup pins both identifiers. The UI exposes bounded states for loading, read-only draft evidence, accountable SME confirmation, publication-in-progress, read-only published evidence, permission denial, stale evidence, incomplete evidence, and indeterminate publication.

## Governed interaction requirements

| Requirement | Executable evidence |
| --- | --- |
| Load fresh purpose-authorized Job evidence | `idle` → `loading` with `aria-busy` and duplicate-action prevention |
| Keep Task/FJA/KSAO/model-assisted evidence non-authoritative until review | `draft` is read-only and explicitly says it is not published Job truth |
| Require accountable human SME confirmation before publication | `review` is `high-risk-confirmation` and requires Job scope, evidence/provenance, limitations, actor, purpose, reason, and evidence version |
| Never turn UI review into candidate/compensation/employment-decision authority | `review` explicitly excludes ranking, rejection, progression, compensation, and employment-decision authority |
| Do not claim success while publishing | `publishing` disables duplicate action and explicitly says in-progress is not proof of publication |
| Claim published state only from authoritative evidence | `published` requires authoritative Job Analysis publication plus immutable audit evidence and remains read-only |
| Fail closed when authority/evidence is unavailable | `denied`, `stale`, `evidenceBlocked`, and `error` expose alert semantics and concrete next actions |
| Reject prototype-chain state confusion | exact built-in strings plus `Object.hasOwn(STATE_MODELS, state)` reject `constructor`, `toString`, and `__proto__` |
| Minimize protected values | generic state models exclude Job identifiers/titles, Job Analysis identifiers/version, effective dates, Task/FJA/KSAO values, source content/URLs, SME identity, candidate/person/position/assignment values, compensation, credentials/tokens, prompts, and model output |

## Contract-first RED and root repair

- Contract head `15c6328d2491009ffca40faaa28d38bb01ca0238` intentionally contained the focused regression and exact-coverage workflow before the production state module existed.
- `HR Workspace Job Architecture State Quality` run `33169736884`, job `98843660150`, checked out and proved that exact SHA, used Node 24.19.0, and terminated **FAILURE** at the focused test with `ERR_MODULE_NOT_FOUND` for the intentionally absent `apps/hr-workspace/job-architecture-state.js`. This is the genuine hosted RED.
- Root implementation commit `d24e1069c549f9be33b164d0ab0237b4b080b513` adds only the bounded presentation state model and markup contract.
- The immediate root-repair run `33169821181`, job `98843941265`, is terminal **GREEN**: exact checkout/proof, Node setup, focused contract under exact 100% line/branch/function thresholds, and clean checkout all succeeded.

Subsequent CSS, Storybook, doctoring, and traceability commits advance the branch head, so the root GREEN above is historical repair evidence rather than passing evidence for the final branch head. The current exact head must obtain its own new terminal GREEN before this active PR can be considered internally consistent, and it remains stack-local even then.
