# Orgmetra Employment Separation Review

This package creates a **pre-mutation review packet** for employment separation. It is intentionally not a termination engine, payroll calculation, benefits processor, identity revocation client, legal conclusion, or automated employment decision.

## What the packet proves

A packet binds one tenant and proposed employment separation to exact opaque references and SHA-256 evidence for:

- the authoritative Person and Employment record;
- the active Assignment/Job/Position scope snapshot to be resolved at review time;
- the reviewed employment-separation policy and process;
- value-free final-pay and benefits handoffs;
- access-deprovisioning, asset-return, knowledge-transfer, and communication plans; and
- separate requester and accountable reviewer actors.

The packet also carries a bounded positive `evidence_version` in canonical evidence so a later review contract cannot be mistaken for an earlier one.

Opaque Person and Employment references remain sensitive correlating metadata. The packet deliberately excludes names, email addresses, protected-attribute values, compensation or benefit amounts, disciplinary or medical narrative, credentials, allocation values, and free-form model output.

## Human authority and owner boundaries

`scope_verification_state` remains `requires_authoritative_resolution`, `mutation_state` remains `not_authorized_to_apply`, and `external_execution_state` remains `not_authorized_to_execute`. The packet cannot be directly constructed or modified into an approved/executed state.

The reviewer must verify the live Employment and every active Assignment/Job/Position represented by the bound snapshot, the proposed date, policy/process evidence, final-pay and benefits handoffs, access deprovisioning, asset return, knowledge transfer, and communication provenance. Only after accountable human approval may the employment mutation proceed through the authoritative Orgmetra People boundary. Downstream actions must use their published owner contracts; this package neither stores provider credentials nor executes foreign-service operations.

## Reason metadata

Free-form separation reasons are excluded because they can become a sensitive narrative side channel. `reason_code` is limited to reviewed operational categories:

- `voluntary_resignation`
- `retirement_transition`
- `fixed_term_completion`
- `position_elimination`
- `employer_initiated_separation`

These categories are routing/governance metadata only. They do not prove legal sufficiency, cause, fairness, or final approval.

## Evidence semantics

`canonical_json()` produces deterministic, precision-preserving, explicitly versioned correlation evidence and `sha256_digest()` hashes those exact UTF-8 bytes. A digest proves only the identity/integrity of this governance envelope; it does not prove the truth of referenced evidence or completion of any HR, payroll, benefits, identity, or security action.
