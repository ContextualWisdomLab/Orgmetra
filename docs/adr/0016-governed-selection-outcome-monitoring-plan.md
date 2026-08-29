# ADR 0016: Governed selection-outcome monitoring plan

- **Status:** Proposed — active PR only
- **Decision scope:** Selection validity / workforce intelligence governance

## Context

Orgmetra already owns Job-scoped selection and post-hire evidence boundaries, but protected `develop` does not define a buyer-facing contract for planning recurring selection-outcome monitoring without copying candidate-level protected-attribute values or turning a screening heuristic into an automated legal or employment decision. Different opaque requester/reviewer references also do not prove that the authoritative actor boundary resolves them to different accountable people, and valid UUID-backed references alone do not prove that all referenced evidence belongs to the packet tenant. Packet-owned UUIDv1 trust references additionally embed timestamp/node-derived correlation metadata. The authoritative tenant identifier is different: it is issued by Orgmetra core, so this leaf package must accept the canonical non-sentinel operational UUID contract owned by that boundary rather than silently imposing a second version policy.

The EEOC's common interpretation of the Uniform Guidelines directs users to examine the total selection process first for each job, describes the four-fifths rule as a rule of thumb rather than a legal definition, and notes that small samples, statistical significance, practical significance, and other evidence can matter. ISO 30405:2023 also treats reviewing and learning as part of recruitment practice. SIOP's fifth-edition Principles provide the professional validation framework for personnel selection procedures.

## Decision

Orgmetra will expose a transport-neutral `SelectionOutcomeMonitoringPlan` that binds:

- one canonical non-sentinel operational tenant under the authoritative Orgmetra core contract and one authoritative Job;
- one total selection-process reference;
- exact aggregate population and selection-outcome snapshot references and SHA-256 digests;
- exact protected-attribute handling, small-sample interpretation, and statistical-analysis plan references and digests;
- an accountable requester reference and an accountable reviewer reference;
- fixed purpose and reviewed reason metadata plus a bounded positive `evidence_version` that is part of canonical evidence;
- an explicit monitoring business-date window and evidence-generation instant.

`tenant_record_id` must be canonical and non-sentinel under Orgmetra's authoritative operational UUID contract. The package does not reinterpret its UUID version because tenant identity generation and migration policy belong to the authoritative HRIS boundary. Packet-owned namespaced trust-bearing references separately require canonical non-sentinel UUIDv4 plus their expected prefix. UUIDv1 and other non-v4 suffixes fail closed for those references. Human-readable, value-bearing, sentinel, and noncanonical reference suffixes are also rejected so labels, policy values, protected-attribute concepts, or actor names cannot be carried through fields represented as opaque identifiers. `evidence_version` must be a true integer from 1 through 2147483647; changing it changes canonical JSON and the packet SHA-256, so revisions to actor/purpose/reason-bound evidence cannot silently collide.

UUID syntax is not tenant authority. Before review, the host must re-resolve **every packet reference** within the exact `tenant_record_id` through the relevant authoritative boundary and reject review use if any reference belongs to another tenant or cannot be authoritatively resolved. The packet also rejects identical requester/reviewer references as an early syntactic guard; after tenant-scoped resolution, the host must prove that the two references resolve to distinct actor identities. Reference inequality alone is not separation-of-duties evidence.

The contract is aggregate-only and carries no candidate identity, protected-attribute value, individual assessment score, individual employment decision, or free-form model output. It fixes `analysis_scope` to `total_selection_process_by_job`, `decision_authority` to `human_review_only`, and state to `requires_human_review`. It does not calculate selection rates, mechanically apply the four-fifths heuristic, test statistical significance, infer discrimination, or authorize a process change.

Each live plan identity receives one process-local construction seal over its exact canonical bytes. Seal registration is one-shot: a repeated `__post_init__()` call cannot overwrite the original seal, including after low-level mutation to another syntactically valid value. Canonical export therefore continues to compare the live payload with the original construction evidence instead of permitting reinitialization to renew trust. This runtime mechanism is defense-in-depth only and does not replace durable immutable audit/outbox evidence, persistence uniqueness, or cross-process authorization.

Any later analytics or persistence boundary must independently enforce purpose-bound authorization, authoritative tenant-scoped reference and actor resolution, minimum-necessary protected-attribute access, small-sample controls, provenance, immutable audit evidence, and accountable human interpretation. Results are evidence for review, not an automated high-impact employment decision or certification/legal conclusion.

## Consequences

- Buyers obtain a deterministic, explicitly versioned governance envelope for recurring selection monitoring without creating a second psychometrics/statistics engine inside Orgmetra.
- The total-process-by-Job scope is explicit before any future component drill-down.
- Privacy risk is reduced because individual protected-attribute values and candidate records remain outside the plan envelope and packet-owned trust references reject UUIDv1 timestamp/node metadata and value-bearing suffixes without making the leaf package incompatible with authoritative Orgmetra tenant UUIDs.
- Cross-tenant evidence mixing is fail-closed at the host review boundary because every opaque reference must be re-resolved in the exact packet tenant.
- Requester/reviewer separation is proven from authoritative resolved actor identities rather than inferred from different opaque strings.
- A valid-value low-level rewrite cannot be legitimized by re-running dataclass initialization because process-local seal registration is single-use for the live identity.
- The four-fifths rule cannot be represented as an automatic pass/fail legal rule by this contract; interpretation remains with authorized analysts and accountable humans.
- Psychometric/statistical production compute remains owned by the appropriate Psychometrics Commons / fast-mlsirm / TEPP contract when those kernels are needed.

## References

See `docs/doctoring/selection-outcome-monitoring-references.md`.
