# ADR 0101: Governed Job grade design review evidence

Status: **Accepted in active PR only; not protected-main truth until integrated**

## Context

Protected `develop` persists authoritative Job identity and governed Job Analysis snapshots, but it has no evidence boundary for reviewing an enterprise-local Job grade/band proposal. Treating a grade code as an ungoverned attribute would make it difficult to prove which Job content, evaluation method, grade architecture, reviewer, and point-in-time evidence supported the proposal. It would also invite accidental coupling between Job classification and compensation or employment decisions.

Job evaluation is a distinct organizational design activity. The International Labour Organization's gender-neutral Job evaluation guidance recommends objective evaluation using common criteria and a documented method so that work of equal value can be assessed more transparently and with less discriminatory bias. U.S. Office of Personnel Management material demonstrates one auditable point-factor approach, the Factor Evaluation System, but those federal classification rules are jurisdiction- and employment-system-specific and are not adopted as Orgmetra's enterprise grade standard.

## Decision

Orgmetra will represent a reviewed Job grade/band proposal as a standalone `JobGradeDesignReviewPacket` before any authoritative Job-grade persistence is introduced.

The packet binds:

- one tenant-scoped authoritative Job reference;
- one persisted Job Analysis snapshot reference and exact SHA-256 digest;
- one enterprise-reviewed Job-evaluation method code and definition digest;
- distinct enterprise-local grade and band codes plus the exact grade/band architecture digest;
- distinct requester and accountable reviewer actor correlations;
- a controlled non-sensitive reason code;
- separate human `reviewed_at` and system `recorded_at` UTC instants; and
- fixed governance stating that the packet is reviewed evidence awaiting authoritative resolution and is not authorized to assign a grade or compensation.

Canonical evidence excludes Job text, Person/worker/candidate identity, pay amounts, ratings, free-form narratives, prompts/model output, and credentials. Grade and band codes remain distinct normalized labels; this ADR does not impose a universal ordering or compensation range.

Trust-bearing runtime primitives are exact built-ins. Tenant/Job/snapshot identifiers reject Nil/Max sentinel UUIDs; packet-owned actor correlations use UUIDv4. Creation-time canonical evidence is sealed in a process-local weak registry outside packet-writable slots so later mutation fails closed. That registry is defense in depth only and does not substitute for durable persistence, authorization, tenant isolation, or immutable audit/outbox.

Any future authoritative Job-grade persistence must re-read the same tenant Job, persisted Job Analysis snapshot, evaluation-method definition, and grade/band architecture; verify exact digests and reviewer authority; preserve business/effective and system-recorded time; then emit immutable audit/outbox evidence. It must not infer compensation, Person performance, or employment outcome from this packet.

## Consequences

- Buyers can trace a grade/band proposal to the exact Job Analysis and method/architecture versions reviewed by a human.
- Job architecture remains separate from compensation and high-impact employment decisions.
- Enterprise-specific grade systems can evolve without hard-coding a federal or vendor-specific taxonomy into Orgmetra.
- A later persistence slice is still required before a reviewed proposal becomes authoritative bitemporal Job-grade truth.
- A later UI slice may provide accessible/Storybooked review interaction; this evidence-only slice introduces no material interactive UI and therefore does not fabricate a Figma or Storybook artifact.

## Alternatives considered

### Store grade directly on Job

Rejected. It loses evidence-version provenance and conflates stable Job identity with time-varying reviewed classification.

### Derive grade directly from compensation

Rejected. Compensation and Job value are related business concepts but are not interchangeable authoritative facts, and this would create circular or discriminatory decision risk.

### Adopt U.S. federal FES/GS grades as Orgmetra's universal model

Rejected. FES is useful methodological evidence for auditable factor evaluation, but its standards and grade conversion are specific to U.S. federal classification. Orgmetra stores an enterprise-local method and architecture digest instead.

## References

See `docs/doctoring/job-grade-design-review-references.md` for APA 7 references, source scope, and applicability limits.
