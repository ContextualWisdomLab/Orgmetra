# Organization Hierarchy Change Review

This package records **human review evidence before an Organization Unit parent relationship is changed**. It does not update the HRIS hierarchy itself.

## Why this boundary exists

Moving an Organization Unit under a different parent can change reporting scope, access scope, workforce analytics, downstream approvals, and the interpretation of historical organization structure. A caller therefore must not turn a reviewed request directly into a mutation.

`OrganizationHierarchyChangeReviewPacket` binds the reviewed change to:

- one tenant and one Organization Unit;
- the reviewed current parent and proposed parent, where `None` represents a real root transition rather than a sentinel identifier;
- a business-effective date that remains separate from the review-evidence timestamp supplied by the invoking boundary;
- exact Organization Unit and hierarchy snapshot SHA-256 evidence;
- a controlled purpose and reason;
- distinct accountable requester and reviewer correlations; and
- an explicit evidence version.

The packet deliberately excludes Person PII, worker values, compensation, ratings, free-form personal text, and employment-decision authority.

## What it does not authorize

Every packet remains:

- `requires_human_review`;
- `requires_authoritative_resolution`;
- `not_authorized_to_apply`; and
- `human_review_only`.

Before any later mutation, the authoritative Orgmetra HRIS boundary must re-resolve the Organization Unit, current parent, proposed parent, and hierarchy at the requested business date and current system-recorded cutoff. It must prove same-tenant scope, reject stale current-parent evidence, self-parenting, cycles, and multiple visible parents, re-establish accountable actor separation, verify the reviewed digests/reason, and commit immutable audit/outbox evidence atomically with the mutation. That authoritative transaction must generate or attest its own system-recorded audit/outbox timestamp; packet `recorded_at` is not the transaction clock authority.

## Identifier and evidence rules

HRIS-owned tenant and Organization Unit identifiers accept canonical non-sentinel operational UUID text, including UUIDv7, so this package does not freeze the core identifier version. Packet-owned change references and actor correlations are UUIDv4. Lowercase SHA-256 digests bind evidence without copying the source records themselves.

Caller-defined packet classes are rejected when subclass creation is attempted, before a subclass can replace `__post_init__`, `__getattribute__`, or another validation/emission hook. Caller-defined subclasses of trust-bearing strings, integers, dates, or datetimes are likewise rejected at issuance. Issuance captures every trust-bearing field once, applies the complete semantic contract to that one snapshot, canonicalizes only those captured values, and derives both the creation digest and live-reference key from the same snapshot. A low-level mutation after one semantic check has run therefore cannot become silently sealed as reviewed evidence.

Issuance is single-use for one live packet object. Closure-private process-local state reserves an object before semantic validation begins; a direct or concurrent second `__post_init__()` call fails closed if that object is already issuing or has already been issued. The lock, creation-digest map, creation-canonical-payload map, creation-state map, in-progress set, weak live-reference map, and packet-retention map are not exposed as module-level mutable registry handles. This prevents ordinary module consumers from deleting or substituting the evidence that enforces same-object re-entry, post-issuance integrity, and still-live reference correlation. Independent packet objects remain concurrent, and failed first-time validation releases the reservation.

The digest verifier is bound inside that same packet runtime when the methods are created. Creation sealing, canonical export verification, and `sha256_digest()` therefore use one captured SHA-256 implementation rather than dynamically trusting the later module-level `sha256` name. Replacing that name after issuance cannot forge a changed live packet into matching its creation seal.

The top-level issuance semantic validator is bound at the same packet-runtime construction boundary. Replacing the later module-level `_validate_issuance_snapshot` name therefore cannot turn mandatory requester/reviewer separation, controlled-purpose/reason, PII minimization, temporal, identifier, or review-state checks into a no-op before the creation seal is written.

That captured validator and the canonicalization path also bind the source-module validation/canonicalization dependencies and fixed governance vocabulary that they use. Ordinary later reassignment of `_validate_reference`, `_validate_digest`, `_validate_code`, timestamp/type helpers, UUID/pattern bindings, or the module constants that define the accepted purpose/reason/states therefore cannot silently change the semantics of an already-constructed packet runtime. The boundary remains deliberately narrow: it does not defend against deliberate mutation of function defaults/closures/globals internals, interpreter/native-memory manipulation, or arbitrary same-process code execution, and it does not replace durable HRIS authorization or persistence.

Snapshot selection and canonical-byte construction use the same boundary. The packet runtime captures `_snapshot`, `_payload_from_snapshot`, `_canonical_payload_json`, and the `_LiveReferenceBinding` constructor before packet construction. Issuance therefore validates, canonicalizes, seals, stores exact field state, derives the live-reference key, and instantiates the digest-conflict guard from runtime-selected authorities even if a later consumer reassigns those module names. This prevents ordinary module mutation from validating one object or snapshot while sealing different evidence, or replacing the still-live reference comparison object with caller-controlled equality behavior. It does not create a general Python sandbox.

The public packet builder follows the same authority rule. At package import, both the package-root builder and the implementation-module builder name are bound to a closure that retains the governed `OrganizationHierarchyChangeReviewPacket` constructor selected at that boundary. A later ordinary reassignment of `review.OrganizationHierarchyChangeReviewPacket` therefore cannot make either public builder instantiate a permissive replacement and bypass requester/reviewer separation or another packet invariant. Deliberate closure/function-global/native-memory manipulation remains outside this process-local defense-in-depth claim.

Canonical export also does not delegate its post-issuance trust decision to the mutable module-level `_payload` or serializer helpers. At issuance the runtime retains the exact canonical JSON and an exact ordered field state in closure-private process-local evidence. At export it reads the retained packet slots once through a runtime-bound base attribute accessor, compares every runtime type and value against that issuance state, verifies the stored canonical bytes against the issuance digest, and returns those already-sealed bytes only when all checks match. Replacing `_payload` after issuance with stale pre-mutation data therefore cannot make a changed retained packet pass. A low-level mutation that occurs after one export state capture cannot alter the bytes selected for that in-flight export, while a later export observes and rejects the changed live state.

`recorded_at` has one additional nested-runtime check before export equality. An exact built-in `datetime` can still contain caller-defined `tzinfo`; Python datetime comparison may invoke that object's `utcoffset()` behavior. The packet runtime therefore requires both the current and issued `recorded_at` values to retain the exact built-in fixed-offset timezone type captured at runtime construction before performing datetime equality. A post-issuance custom-`tzinfo` substitution fails closed without executing the nested timezone callback. This is still process-local defense in depth, not a Python sandbox.

These controls are narrow process-local defense in depth, not a claim that the package can sandbox arbitrary in-process code, deliberate closure introspection, native memory mutation, or malicious extensions. Module-level payload helpers remain deterministic validation utilities only; they are not post-issuance evidence authority.

`recorded_at` is a review-evidence timestamp supplied by the invoking boundary. Construction proves canonical built-in fixed-offset representation and rejects a value later than the current UTC clock at issuance, but this leaf package does not prove which clock generated the value. That provenance distinction is intentional: NIST SP 800-53 AU-8 clock ownership belongs at the authoritative audit-generating system boundary. Later canonical export validates the retained exact issuance state and digest without consulting the wall clock, so a backward clock adjustment cannot invalidate evidence that was validly issued.

A tenant-qualified `organization_hierarchy_change_reference` is also bound to one evidence digest while any idempotent packet carrying that reference remains alive in the process. An exact duplicate is allowed; a different reason, parent, timestamp, digest, actor, or other trust-bearing value under the same still-live reference fails closed. This prevents `dataclasses.replace()` or a second constructor call from silently minting conflicting live review evidence under one packet correlation.

The closure-private in-process creation seal, issuance canonical payload/state, captured semantic validator and its ordinary module-binding dependencies, direct issuance-helper and live-reference-constructor bindings, public builder constructor binding, digest verifier, single-use issuance reservation, and live-reference binding are defense in depth only. They are not durable database uniqueness, distributed authorization, restart-stable identity, authoritative timestamp provenance, or a substitute for the authoritative audit/outbox transaction. Durable persistence must enforce tenant-qualified uniqueness, authoritative system time, and immutable evidence independently.

## Quality contract

Canonical Foundation CI builds one exact wheel, binds its SHA-256 at install time, executes tests against the installed artifact on CPython 3.14.7, requires exact 100% owned statement and branch coverage, and proves the checkout is clean. The retired repository-owned feature workflow must not be resurrected. Recovery, SAST, security, and other centrally required workflows remain separate exact-head evidence.
