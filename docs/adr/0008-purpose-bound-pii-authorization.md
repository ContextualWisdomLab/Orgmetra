# ADR 0008: Purpose-bound PII authorization

- Status: Accepted on active implementation branch
- Date: 2026-08-17
- Owners: Orgmetra Security / People API

## Context

Orgmetra must keep necessary HR PII usable for authorized work without turning authentication, a broad role, or a caller-supplied purpose label into blanket access. Keyverse owns authentication and identity evidence; Orgmetra owns the employment-policy decision about which HR resource fields may be used for which tenant, purpose, and operation. The Keyverse repository remains a read-only dependency and Orgmetra consumes only its published identity/scope contract.

NIST SP 800-162 defines attribute-based access control as evaluating subject, object, requested operation, and environment attributes against policy. NIST SP 800-205 further emphasizes the quality and trustworthiness of attributes used by an access-control decision. NIST Privacy Framework 1.0 supplies the current final privacy-risk management baseline for governing data processing. A declared purpose is therefore one authorization attribute, not a substitute for authenticated subject context, tenant isolation, exact resource identity, operation-specific capability, or field minimization.

## Decision

Orgmetra will enforce purpose-bound PII authorization inside `orgmetra_keyverse_adapter` before protected field values leave the authoritative HR boundary.

`PurposeBoundAccessRequest` carries only authorization attributes: active tenant, authenticated actor tenant, resource tenant, opaque actor reference, opaque target-resource reference, purpose, requested operation, resource kind, requested field names, and granted operation scopes. The opaque target reference is mandatory so authorization evidence can be correlated to the exact Orgmetra record without retaining that record's protected field values. Its namespace must exactly equal the declared `resource_kind`, preventing a decision for one HR resource type from preserving audit evidence that identifies another type. `PurposeBoundAccessPolicy` is Orgmetra-owned and binds one tenant to one policy version, resource kind, purpose, operation, required Keyverse-derived scope, and immutable permitted field set.

Evaluation fails closed unless all of the following hold:

- request, authenticated actor, target resource, and policy resolve to the same tenant;
- the opaque target-reference namespace exactly matches the request's resource kind;
- resource kind, purpose, and operation exactly match the policy;
- the authenticated principal carries the policy's explicit operation-specific Orgmetra scope;
- requested fields are a non-empty subset of the policy's permitted fields;
- UUIDs, opaque actor and resource references, codes, scopes, resource kinds, and field sets are syntactically explicit and reject reserved sentinels, wildcard-like values, ambiguous mutable collections, and malformed identifiers.

The authorization decision contains only governance metadata, including the opaque actor and exact target-resource references, and authorized field names, never protected field values. Denials expose a stable reason code and a customer-facing next action without copying PII. An allow decision authorizes only the exact requested field subset; it does not widen the request to every field permitted by the policy. Both allow and denial evidence retain the exact opaque target reference so a later immutable audit event cannot become ambiguous about which HR record was evaluated.

The adapter does not store passwords, passkeys, bearer tokens, or raw credentials. It does not ask Keyverse to make an Orgmetra employment-policy decision, and it does not directly read or mutate Keyverse storage. Persistent policy administration, retention, and export-control workflows remain separate Orgmetra slices; this ADR establishes the decision contract they must preserve.

## Consequences

### Positive

- Necessary HR PII remains usable for legitimate work while access is narrowed by tenant, resource, purpose, operation, scope, and field.
- Cross-tenant confused-deputy paths fail before resource details are disclosed.
- A target reference cannot be relabeled as another HR resource kind while remaining valid audit evidence.
- A purpose header or broad identity token cannot silently widen field access.
- PII-minimized decisions can be bound into the governed audit/outbox envelope with exact target correlation and without duplicating protected field values.
- The integration remains modular: Keyverse authenticates and publishes identity attributes/scopes; Orgmetra owns HR authorization policy and decisions.

### Costs and limitations

- Separate purposes, operations, and resource kinds require separately governed policy records; there is intentionally no wildcard policy form in this contract.
- Callers must resolve trusted tenant/resource attributes and one opaque target-resource reference before requesting protected values.
- Policy persistence, administrative UX, delegated policy lifecycle, retention, export controls, and cryptographic policy-signing are subsequent Orgmetra boundaries and must not be inferred as implemented by this ADR.

## Verification

The executable authorization matrix proves same-tenant binding, exact opaque target correlation, exact target-namespace/resource-kind binding, resource/purpose/operation matching, operation-specific scope, exact field minimization, fail-closed malformed and mutable attributes, reserved UUID rejection, PII-minimized decisions, actionable denial metadata, and exception behavior. The owned `orgmetra_keyverse_adapter` production surface is required to maintain exact 100% statement and branch coverage where the pinned CI toolchain exposes those metrics.

## References

The APA 7 bibliography is maintained in `docs/doctoring/REFERENCES.md`, including NIST SP 800-162, NIST SP 800-205, and NIST Privacy Framework 1.0. Draft successors are research inputs only until NIST publishes a final replacement.
