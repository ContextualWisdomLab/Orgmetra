# ADR 0096: Govern Organization Unit hierarchy changes before mutation

## Status

Active PR only. This ADR is not protected-main truth until the owning PR is integrated.

## Context

Orgmetra already treats Organization Unit hierarchy as bitemporal HRIS truth. A parent change can alter organizational scope used by reporting, authorization, analytics, and downstream workflows. A reviewed request must therefore remain distinct from the authoritative mutation that changes HRIS truth.

A pre-mutation evidence packet also needs to represent moving an Organization Unit to or from the root without inventing a sentinel parent identifier. It must preserve the requested business-effective date separately from the review-evidence timestamp supplied by the invoking boundary and must not copy Person PII or worker values into durable governance evidence. The leaf package can validate that timestamp's canonical fixed-offset representation and reject a future issuance value, but it cannot prove which clock generated the caller-supplied value. Under NIST SP 800-53 Rev. 5 Release 5.2.0 AU-8, authoritative audit timestamp provenance belongs to the internal system-clock owner at the mutation/audit boundary, not to this leaf value object.

The packet-owned hierarchy-change reference is itself audit correlation. Reissuing a different valid payload under the same still-live tenant-qualified reference would make that correlation ambiguous even if each individual payload passed field validation. A frozen dataclass is not a complete trust boundary by itself because low-level `object.__setattr__` can still replace an issued scalar with a caller-defined runtime subtype. If that subtype serializes to the same JSON primitive value, a digest-only export check cannot distinguish the representation change even though executable caller-owned behavior remains attached to the live packet. Export also must not validate one read of a live packet and serialize later reads: concurrent low-level mutation between those phases would make the checked evidence and emitted evidence different observations. The same checked-versus-used rule applies at issuance: semantic validation cannot read the live packet and then let creation sealing reread it, because a value changed after its validator ran could otherwise become the value bound into the issuance digest without ever receiving semantic validation. A further boundary is required because `__post_init__()` remains an ordinary callable method: after valid issuance, low-level mutation to a fresh change reference followed by a second `__post_init__()` call must not be allowed to replace the creation seal for the same live packet object.

Fresh review also found that a correct process-local algorithm is not sufficient if its mutable backing registries are ordinary module globals. Direct handles to creation digests, issuance reservations, weak live-reference bindings, or packet-to-binding retention would let ordinary same-interpreter consumers dismantle the defense-in-depth state that the packet contract claims to maintain. The mutable state therefore has to remain private to the packet runtime rather than merely carrying underscore-prefixed module names.

The verifier is part of that same trust boundary. Keeping the creation digest private is insufficient if creation sealing or later export verification dynamically resolves a mutable module-level digest constructor. An ordinary same-interpreter consumer that retains the valid digest could otherwise mutate live evidence and replace that module binding so the changed payload appears to match the creation seal. The packet runtime therefore must bind its evidence-digest implementation when its methods are constructed, while leaving unrelated validation helpers available as deterministic test seams.

The same capability rule applies to payload selection after issuance. A closure-private `canonical_json()` method is still forgeable if it dynamically calls a replaceable module-level `_payload` or serializer helper after evidence has been issued: a consumer can retain the original payload, mutate a trust-bearing slot, replace the helper with one that returns the original payload, and make the digest comparison observe stale evidence rather than the retained live packet. Export verification must therefore bind the issuance state and issuance canonical bytes inside the same private runtime and compare one direct exact-slot snapshot against that state before returning the already-sealed canonical bytes. A module helper may remain available for deterministic validation, but it is not part of the post-issuance trust decision.

## Decision

Introduce a bounded `OrganizationHierarchyChangeReviewPacket` that records only the reviewed change correlation and governance evidence.

The packet:

1. binds one tenant and one Organization Unit to the reviewed current and proposed parent;
2. permits `None` only for a real root attachment/detachment and rejects a no-op where current and proposed parents are equal;
3. rejects self-parenting locally but does not pretend that a leaf packet can prove the full hierarchy is acyclic;
4. keeps `effective_on` separate from `recorded_at`, treating the latter as review evidence supplied by the invoking boundary rather than as authoritative transaction-clock proof;
5. binds reviewed Organization Unit and hierarchy snapshots by lowercase SHA-256 digest instead of copying HR record values;
6. requires distinct requester and reviewer correlations, one fixed purpose, one controlled reason, and explicit evidence versioning;
7. fixes review/scope/mutation/decision-authority states so the packet can never authorize the mutation itself;
8. rejects caller-defined packet classes at subclass creation, before they can replace `__post_init__`, `__getattribute__`, or another validation/emission hook, and also rejects caller-defined trust-bearing primitive subclasses at issuance;
9. captures every trust-bearing field exactly once into one creation snapshot, runs the complete issuance semantic contract on that snapshot, canonicalizes only that snapshot, and derives both the creation digest and live-reference key from it, so no after-validation reread can be sealed as reviewed evidence;
10. reserves each packet object for exactly one issuance attempt in closure-private process-local state and rejects a packet that is already issued or concurrently issuing, so a later direct `__post_init__()` call cannot reseal the same object under a different reference or reviewed value and ordinary module consumers receive no registry mutation handle;
11. stores the exact issuance canonical JSON and exact issuance field state in closure-private process-local state; canonical export captures the retained object's trust-bearing slots once through the runtime-bound base attribute accessor, compares exact runtime type and value against the issuance state, validates the stored canonical bytes against the issuance digest, and returns those already-sealed bytes only when all checks match;
12. binds each still-live `(tenant_record_id, organization_hierarchy_change_reference)` to one canonical evidence digest while allowing exact idempotent duplicate packets to share that binding, with the weak binding and packet-retention registries held in the same closure-private runtime state;
13. captures the SHA-256 implementation inside that private packet runtime and uses it consistently for creation sealing, export verification, and the public evidence digest, so replacing the later module-level `sha256` name cannot forge a changed live packet into matching its creation seal; and
14. keeps module-level payload/canonicalization helpers outside the post-issuance verifier authority, so replacing `_payload` or a serializer after issuance cannot substitute stale pre-mutation evidence for the retained packet's direct slot state.

The leaf timestamp contract is deliberately limited: issuance validates fixed-offset representability and rejects a `recorded_at` value later than the current UTC clock, while export remains deterministic and does not recheck wall-clock freshness. This establishes representation and issuance chronology only. It does not attest that an internal system clock generated the supplied value. The authoritative application/audit transaction must generate or attest its own system-recorded timestamp and must not promote packet `recorded_at` into durable transaction-time authority.

The issuance reservation is weak/process-local and identity-scoped. It exists only to prevent re-entry of the same packet object while issuance is in progress or after that object has been issued; independent packet objects may validate concurrently. The reservation is cleared after a failed initial issuance so invalid never-issued raw objects do not leak registry state. Its mutable lock, creation-digest map, creation-payload map, creation-state map, in-progress set, live-reference map and packet-retention map are captured behind the packet methods rather than exported as module-level mutation capabilities.

The digest and export bindings are likewise process-local defense in depth. They prevent ordinary replacement of module digest/payload helper names from changing the evidence verifier used by the packet runtime; they are not a sandbox against arbitrary same-process code execution, deliberate closure introspection, interpreter/native-memory mutation, or a substitute for durable signed/audited persistence.

The live-reference binding is deliberately weak/process-local: a shared binding object remains alive while any idempotent packet using that reference remains alive, so collection of one duplicate cannot erase the binding for another. Once every packet is gone or the process restarts, durable uniqueness must come from authoritative persistence rather than this leaf package.

The next boundary must re-resolve the Organization Unit, current parent, proposed parent, hierarchy and accountable actors against authoritative same-tenant bitemporal HRIS truth. It must reject stale current-parent evidence, self-parenting, cycles and multiple visible parents, verify the reviewed evidence, generate or attest authoritative system-recorded audit time, and persist the resulting mutation with immutable audit/outbox evidence in the authoritative transaction.

## Identifier ownership

Tenant and Organization Unit identifiers are HRIS-owned operational identifiers. The packet therefore accepts canonical non-sentinel UUID text without freezing them to UUIDv4; UUIDv7 remains interoperable. Packet-owned change references and actor correlations use UUIDv4 opacity. This distinction avoids forcing leaf-package identifier policy onto the authoritative HRIS owner.

## Privacy and security rationale

The packet contains no Person identifier, worker value, compensation, rating, free-form personal reason, credential, or employment-decision authority. Purpose, reason, requester/reviewer separation, immutable correlation evidence and later authoritative audit support separation-of-duties and accountability without claiming certification.

NIST Privacy Framework 1.0 remains the current final Privacy Framework baseline; NIST describes Privacy Framework 1.1 as an Initial Public Draft with the final update still forthcoming. NIST SP 800-53 Rev. 5 Release 5.2.0 is the current finalized minor release used for security/privacy-control context. AU-8 requires internal system clocks to generate audit-record timestamps and UTC/fixed-offset-compatible representation; this leaf packet implements the representation/chronology part only and leaves clock provenance to authoritative audit generation. UUID syntax and version semantics follow RFC 9562.

## Consequences

- Buyers gain an explicit review artifact for organization-structure changes instead of conflating approval evidence with mutation authority.
- Root transitions remain representable without reserved/sentinel parent identifiers.
- Conflicting in-process evidence cannot silently reuse a still-live hierarchy-change correlation; exact idempotent duplicates remain possible.
- Issuance semantic validation and creation sealing consume one identical captured snapshot; a live-object mutation after capture cannot become silently sealed reviewed evidence, and any later export of changed live state is rejected against the closure-private issuance state.
- The same live packet object cannot be manually or concurrently reissued after its issuance reservation is acquired; direct re-entry fails closed rather than replacing its creation digest under a fresh reference.
- Ordinary module consumers no longer receive mutable handles to the process-local issuance registries, so they cannot erase creation evidence or packet-retention bindings through normal module-state mutation while the packet is still live.
- Creation sealing, export verification, and public digest reporting share one runtime-bound SHA-256 implementation, so ordinary replacement of the module digest name cannot make mutated evidence pass the creation-seal comparison.
- Canonical export observes the retained packet exactly once through direct slot reads, compares exact type/value state with the closure-private issuance state, and returns the exact canonical JSON sealed at issuance; replacing a module `_payload`/serializer helper after issuance cannot make stale payload bytes authorize a changed live packet.
- `recorded_at` remains deterministic review evidence, but the leaf package does not overclaim authoritative clock provenance. Durable audit/outbox time is generated or attested by the authoritative transaction boundary.
- The slice stays independently deployable and does not depend on direct cross-service application-table access.
- Process-local tamper/reference/digest/export detection is defense in depth only; durable uniqueness, authorization, concurrency control, hierarchy validation, authoritative system time and audit remain responsibilities of authoritative persistence/orchestration boundaries.
