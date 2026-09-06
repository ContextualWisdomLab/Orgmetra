# ADR 0111: Govern Position lifecycle-change review separately from mutation

Status: Proposed

## Context

Current `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` product truth stores Job, Position, and Assignment separately and already recognizes Position lifecycle vocabulary, but the shipped People mutation path only creates Position records. Repository governance is a separate concern: effective organization ruleset `18156473` currently requires one approving review, stale-review dismissal after push, review-thread resolution, extra approval for unattributed changes, seven central required workflows, and non-fast-forward/deletion protection; `require_last_push_approval` is false. Issue #89 owns the remaining governance/control-plane gap, including routine `OrganizationAdmin/always` bypass. None of those repository controls is implied by this ADR, and their live payload must be re-read before integration/release claims. Vacancy evidence and vacancy-to-assignment orchestration do not own a review contract for freezing, closing, abolishing, or reactivating an existing seat.

A lifecycle change can affect staffing availability and later workforce evidence. Reusing a generic Position-creation command or a reporting-line review would blur evidence ownership and could let cached/UI state substitute for current bitemporal truth.

## Decision

Add an Orgmetra-owned `PositionLifecycleChangeReviewPacket` as a transport-neutral, value-minimized human-review artifact.

The packet binds one tenant-qualified Position, current/proposed lifecycle state, business-effective date, reviewed Position/Assignment snapshot digests, pseudonymous requester/reviewer separation, controlled reason/outcome, evidence version, and human-review/system-recorded UTC chronology. `abolished` is terminal and no-op transitions are rejected.

The packet never authorizes mutation. An approved review remains `requires_authoritative_resolution` and `not_authorized_to_apply`. The later authoritative host must freshly resolve bitemporal Position and Assignment truth, re-establish actor authority/separation and staffing safety, validate the reviewed evidence, and commit the mutation with immutable audit/outbox.

Package-level quality remains subordinate to protected repository ownership: the retired Position Lifecycle Review leaf workflow stays deleted. Its useful exact CPython 3.14.7, installed-wheel provenance, and 100% statement/branch coverage obligations execute through canonical Foundation CI with an executable non-resurrection regression.

## Consequences

- Lifecycle review evidence cannot silently become Position truth.
- Existing Position/Assignment source-of-truth boundaries remain unchanged.
- No Person/candidate identity, compensation, assessment, rating, allocation value, credential, prompt, or model output is copied into the review evidence.
- A later bounded mutation/persistence slice remains necessary; this ADR does not claim it is shipped.
- Process-local issuance/reference binding is defense in depth, not distributed durability or authorization.
- Conflict-free Git protected-parent adoption is insufficient if it resurrects a workflow retired by the protected owner; semantic reconciliation must preserve the protected owner and the useful evidence contract separately.

## Alternatives rejected

1. **Encode lifecycle change as a new Position creation.** Rejected because it would conflate stable Position identity with versioned lifecycle state.
2. **Reuse vacancy or reporting-line review evidence.** Rejected because those artifacts prove different facts and do not own lifecycle semantics.
3. **Allow the review packet itself to mutate Position truth.** Rejected because current Position/Assignment truth and staffing safety must be re-resolved at the authoritative transaction boundary.
4. **Restore the package-local quality workflow during protected-parent adoption.** Rejected because protected #161 centralized repository-owned PR quality and pinned the canonical runner contract; the package's useful artifact/coverage obligation belongs under that owner rather than in a resurrected leaf.
