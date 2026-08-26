# Orgmetra Employment Separation Review

This package creates a **pre-mutation review packet** for employment separation. It is intentionally not a termination engine, payroll calculation, benefits processor, identity revocation client, legal conclusion, or automated employment decision.

## What the packet proves

A packet binds one authoritative Orgmetra `tenant_record_id` and proposed employment separation to exact SHA-256 evidence plus opaque packet-owned namespaced trust references for:

- the authoritative Person and Employment record;
- the active Assignment/Job/Position scope snapshot to be resolved at review time;
- the reviewed employment-separation policy and process;
- value-free final-pay and benefits handoffs;
- access-deprovisioning, asset-return, knowledge-transfer, and communication plans; and
- separate requester and accountable reviewer references, whose authoritative actor identities must still be resolved and proven distinct before approval.

`tenant_record_id` follows protected Orgmetra core's canonical non-sentinel operational-UUID contract, including valid UUIDv7 tenant identities. Packet-owned namespaced trust references remain canonical UUIDv4 so timestamp/node-derived correlation metadata cannot enter leaf-owned opaque references. The packet also carries a bounded positive `evidence_version` in canonical evidence so a later review contract cannot be mistaken for an earlier one.

Opaque Person and Employment references remain sensitive correlating metadata. The packet deliberately excludes names, email addresses, protected-attribute values, compensation or benefit amounts, disciplinary or medical narrative, credentials, allocation values, and free-form model output.

## Human authority and owner boundaries

`scope_verification_state` remains `requires_authoritative_resolution`, `mutation_state` remains `not_authorized_to_apply`, and `external_execution_state` remains `not_authorized_to_execute`. The packet cannot be directly constructed or modified into an approved/executed state.

Immediately before approval, the host must re-resolve **every packet reference within the exact `tenant_record_id` context**. That includes resolving `requester_reference` and `reviewer_reference` through the authoritative actor boundary and proving the resolved actor identities are distinct; string inequality between two opaque references is only an early syntactic guard and is not separation-of-duties evidence. The host must also prove the Person-to-Employment binding and every active Assignment/Job/Position represented by the bound snapshot, then verify the proposed date, policy/process evidence, final-pay and benefits handoffs, access deprovisioning, asset return, knowledge transfer, and communication provenance. Reference syntax and packet digests prove correlation/integrity only; they do not prove tenant ownership, actor identity, or worker relationship validity. Only after accountable human approval may a later authoritative employment-mutation boundary consider the change. Downstream actions must use their published owner contracts; this package neither stores provider credentials nor executes foreign-service operations.

### Accountable approval receipt

`approve_employment_separation(...)` is the explicit human-approval boundary layered on the review packet. It accepts only the exact governed packet runtime type, freezes the approval instant to built-in UTC evidence, requires the approving actor to be the packet's accountable reviewer, snapshots the exact packet bytes and SHA-256 before host work, and calls an `EmploymentSeparationApprovalAuthority` that must freshly re-resolve tenant, Person, Employment, active Assignment/Job/Position, reviewed evidence, reviewer identity/authority, and the exact approval instant. A changed packet, wrong-scope verification, malformed provenance, or non-contract authority result fails closed.

The issued `EmploymentSeparationApprovalReceipt` is value-minimized and permanently remains `human_approved_for_authoritative_resolution`, `not_authorized_to_apply`, and `not_authorized_to_execute`. It does **not** terminate Employment, close Assignments, revoke access, run payroll/final-pay, change benefits, or call a foreign owner. Its canonical evidence is protected against post-issuance rewriting by a process-local HMAC-backed issuance seal outside receipt-writable slots; that mechanism is defense-in-depth for a live Python process, not durable cryptographic attestation. Durable systems must persist the already-issued canonical JSON and SHA-256 through Orgmetra's immutable audit/outbox boundary and must still perform fresh purpose-bound authorization immediately before consequential mutation or external execution.

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
