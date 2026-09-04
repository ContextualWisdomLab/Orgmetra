# ADR 0117: Govern model-assisted Job Analysis drafts as non-authoritative evidence

- Status: Proposed — active PR only
- Decision owner: Orgmetra
- Protected-main baseline when proposed: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df`

## Context

Orgmetra already owns authoritative Job Analysis snapshots, but model-assisted Task/FJA/KSAO drafting needs a separate trust boundary. Sending Job Analysis material to a model before exact tenant/purpose authorization, accepting a model answer without source/snapshot provenance, or treating human-confirmed model text as authoritative persistence would weaken HR governance and create an indefensible high-impact decision path.

Current orchestration research such as Conductor, TRINITY, and Sakana Fugu demonstrates that dynamic coordination and role specialization can improve model-system capability. Those results concern orchestration performance; they do not establish employment-decision validity, Job Analysis content validity, authorization, or accountable human decision authority.

## Decision

Orgmetra will expose a transport-neutral model-draft workflow with four explicit boundaries:

1. **Authoritative scope resolution first.** The workflow binds the exact tenant, Job Analysis reference, Job Analysis snapshot SHA-256, purpose `job_analysis_model_draft`, and requester before any model call.
2. **Semantic-unit provenance.** Runtime evidence must contain canonically ordered, unique Task/FJA/KSAO semantic units. Each unit binds raw runtime text to a content digest and a source-provenance digest. The durable receipt retains only value-minimized digests/references, not raw semantic text.
3. **Untrusted orchestration result.** The injected model adapter returns raw draft text plus its digest, a reviewed exact orchestration revision, orchestration-evidence digest, and route reference. Contextual Orchestrator is a read-only dedicated-writer dependency and is consumed only through this injected host contract.
4. **Accountable human review.** A reviewer distinct from the requester explicitly confirms the draft for later authoritative review or rejects it with a controlled reason. Confirmation does not authorize persistence.

The durable receipt retains the exact authorizing evidence digest and always states `decision_authority=not_authorized_for_job_analysis_persistence`. The authoritative Job Analysis persistence boundary must independently re-resolve current scope, actor authority, evidence, and immutable audit/outbox before any authoritative change.

## Integrity and privacy consequences

Trust-bearing runtime primitives are exact built-in types. Packet-owned references use UUIDv4 suffixes; tenant identity follows the canonical non-sentinel operational UUID contract. Requests and model evidence are snapshotted across injected authority/model/human calls so checked evidence cannot be rewritten between trust boundaries. Issued receipts are value-minimized and use process-local tamper evidence as defense in depth; durable distributed uniqueness and audit authority remain host responsibilities.

Raw Task/FJA/KSAO text and raw draft output are not durable receipt fields. No candidate/person PII, assessment score, compensation value, selection outcome, performance rating, or employment-decision authority is introduced by this package.

## Consequences and alternatives rejected

- Direct model-to-Job-Analysis persistence is rejected because it collapses proposal and authority.
- A generic model-evidence envelope alone is insufficient because Job Analysis requires explicit Task/FJA/KSAO family coverage and exact snapshot binding.
- Duplicating Contextual Orchestrator internals inside Orgmetra is rejected because it violates dedicated-writer ownership and creates orchestration drift.
- Storing raw model prompts/results in durable HR evidence is rejected in this boundary because the buyer/auditor contract needs provenance and review evidence, not unconstrained content retention.

This ADR becomes accepted architecture only after the owning PR integrates into fresh protected-main truth.
