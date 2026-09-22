# Gateway composition boundary references

Verification date: 2026-09-23

Scope: primary standards and authoritative specifications used by ADR 0432, plus exact repository-owner capability evidence needed to avoid assigning product semantics to the wrong runtime. Standards constrain protocol and database behavior; they do **not** prove that Orgmetra, Keyverse, pingora-gateway, or an owner API is released, deployed, conformant, secure, or within the commercial latency target.

## Source-to-decision traceability

### Authentication and authorization boundary

OpenID Foundation. (2023). *OpenID Connect Core 1.0 incorporating errata set 2*. https://openid.net/specs/openid-connect-core-1_0.html

OpenID Connect remains the authentication/claims contract referenced by protected Orgmetra architecture. Keyverse remains identity/issuer authority. Orgmetra consumes a released relying-party verifier/profile and applies its own versioned ACL before a verified subject or organization/workspace claim becomes a runtime actor or tenant coordinate. Downstream purpose/resource authorization remains separate.

Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). *Best current practice for OAuth 2.0 security* (BCP 240, RFC 9700). RFC Editor. https://www.rfc-editor.org/rfc/rfc9700.html

RFC 9700 supports treating bearer-token verification, key rotation, redirect/browser behavior, and identity-backend failure as explicit security boundaries. It does not define Orgmetra tenant, Person binding, business purpose, or HR authorization semantics.

### HTTP semantics, retries, and error preservation

Fielding, R., Nottingham, M., & Reschke, J. (2022). *HTTP semantics* (RFC 9110). RFC Editor. https://www.rfc-editor.org/rfc/rfc9110.html

RFC 9110 constrains method idempotency and retry semantics and defines HEAD in relation to GET. ADR 0432 therefore keeps retry/replay truth with the exact released owner operation contract; ambiguous mutation failure never authorizes a fresh mutation. GET/HEAD share selected-resource collision authority without composition inventing an undeclared method.

Berners-Lee, T., Fielding, R., & Masinter, L. (2005). *Uniform Resource Identifier (URI): Generic Syntax* (RFC 3986). RFC Editor. https://www.rfc-editor.org/rfc/rfc3986.html

RFC 3986 defines complete `.` and `..` path segments as normalization-relevant dot segments. Orgmetra rejects those complete segments before route hashing/admission rather than allowing one manifest identity to normalize into another selected path.

Nottingham, M., Wilde, E., & Dalal, S. (2023). *Problem details for HTTP APIs* (RFC 9457). RFC Editor. https://www.rfc-editor.org/rfc/rfc9457.html

Where an owner publishes RFC 9457 Problem Details, composition preserves owner status/problem identity and does not leak stack traces, credentials, restricted HR payloads, or topology. This citation does not silently migrate protected Orgmetra APIs to RFC 9457.

### OpenAPI contract description

OpenAPI Initiative. (2025). *OpenAPI Specification v3.2.0*. https://spec.openapis.org/oas/v3.2.0.html

Protected Orgmetra `docs/API_CONTRACT.md`, `docs/TRD.md`, `schemas/openapi.yaml`, Foundation validation, and contract tests declare OpenAPI 3.2.0. That remains the protected product contract until its canonical owner changes it.

OpenAPI Initiative. (2026). *OpenAPI Specification v3.2.1*. https://spec.openapis.org/oas/v3.2.1.html

Version 3.2.1 was published on 2026-09-10 and is the current 3.2 patch-level specification on this verification date. OAS 3.2 patch releases clarify the same major/minor feature set; citing 3.2.1 supplies current interpretation and does not silently change Orgmetra's protected 3.2.0 declaration.

The route-admission decisions use these OAS facts separately:

- templated paths with the same hierarchy but different placeholder names are one path identity;
- concrete non-templated paths take precedence over templated counterparts;
- each template expression must be valid and appear at most once;
- one Path Item carries shared path-level semantics such as parameters and servers, so disjoint HTTP methods do not by themselves prove that separately released owners can be merged safely; and
- OAS permits a wider method/path grammar than the current Orgmetra canary.

Orgmetra intentionally implements a narrower fail-closed product-route profile. Broader support requires a released owner use case and explicit conformance evidence rather than permissive parser drift.

### PostgreSQL namespace and function provenance

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Client connection defaults*. https://www.postgresql.org/docs/18/runtime-config-client.html

PostgreSQL places an unqualified newly created object in the first valid schema in `search_path`. The default path is suitable only for mutually trusting users. This directly supports the 0018→0025 rule that migration-session namespace state is not composition authority and that authority relations/functions/targets are explicitly schema-qualified.

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Function security*. https://www.postgresql.org/docs/18/perm-functions.html

PostgreSQL warns that functions, triggers, and policies can act as Trojan-horse execution paths and recommends removing schemas writable by untrusted users from `search_path` and referring only to trusted objects. This is the primary security basis for the hostile-search-path contracts and explicit trigger-function provenance in 0024.

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: CREATE FUNCTION*. https://www.postgresql.org/docs/18/sql-createfunction.html

The `SECURITY DEFINER` guidance requires a safe search path that excludes schemas writable by untrusted users and notes that newly created functions receive `PUBLIC` execute privileges by default unless revoked. Orgmetra's composition migrations do not infer security from a function name alone; object namespace, owner, privileges, and deployment role topology remain separate evidence concerns.

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Privileges*. https://www.postgresql.org/docs/18/ddl-priv.html

PostgreSQL documents `TRUNCATE`, `REFERENCES`, `TRIGGER`, and schema `CREATE` as distinct capabilities and warns that trigger creation can cause code execution during another user's table modification. This supports treating table/function ownership and runtime/migrator privileges as a security boundary rather than relying only on row-level DML triggers.

PostgreSQL Global Development Group. (2026). *PostgreSQL 18 documentation: Overview of trigger behavior*. https://www.postgresql.org/docs/18/trigger-definition.html

PostgreSQL supports row- and statement-level triggers, and `TRUNCATE` triggers are statement-level only. Orgmetra therefore maintains explicit TRUNCATE guards in addition to UPDATE/DELETE append-only guards.

### Database-role limitation of migration provenance

PostgreSQL trigger and relation provenance is necessary but not sufficient for production least privilege. An object owner or superuser can alter objects or defeat ordinary DDL/DML guards. Accordingly, 0025 proves that composition child relations share the parent generation authority owner at migration admission; it does **not** prove that the production runtime login is distinct from the migration/object-owner role. That remains deployment evidence and must be tested before immutable release.

This distinction follows the repository's existing hardening pattern in migration 0008, which separates an externally assignable operator capability from a fresh `NOLOGIN` function-owner role and limits temporary schema `CREATE` privilege to the ownership handoff transaction. The composition stack may adopt an equivalent role model only through an explicit deployment/database-role decision and acceptance tests; 0025 does not invent that topology implicitly.

## Repository-owner capability evidence

These facts are not normative standards. They constrain architecture because CWL consumers must respect the released owner's actual supported contract rather than infer capability from repository existence.

### Orgmetra protected truth

On 2026-09-23 protected authority remains `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`. Protected architecture documents a buyer-facing Gateway, while protected executable truth still has no supported deployable multi-owner product-composition application. Draft implementation responsibilities remain design/implementation evidence, not shipped capability.

### Draft executable stack

- #434 exact `68bdf2d984ca7686219c335a85a6574195675cbe` owns process-local route/generation admission, canonical owner release attribution, deterministic route identity/selection, bounded OpenAPI profile, and construction/use-time integrity.
- #436 exact `5fd0087179f2e6f23f2bb3853ad1de397fc53b0e` owns normalized PostgreSQL generation/configuration authority plus atomic, caller-search-path-independent 0018 publication.
- #437 exact `960a5fbfcb98075862cdbee8ee094a9b8d7dcc55` owns current 0019→0025 activation/recovery authority: evidence-bound transitions, PostgreSQL-clock observation validity, durable recovery attestation, fenced upgrades, shared deployment-row serialization, full-chain schema provenance, trusted trigger-function provenance, generation-anchored child relation ownership, checked-as-used process-local runtime capability integrity, and the recovery commit boundary.

All remain Draft. Synthetic owner-release fixtures, process-local registries, and migration contracts do not prove actual owner releases, Keyverse conformance, Orgmetra identity ACL, production database-role least privilege, deployable HTTP composition, commercial latency, protected integration, or immutable Orgmetra release.

### pingora-gateway owner contract

Previously verified protected pingora-gateway evidence remains transport-oriented and excludes Orgmetra product routing/auth/business semantics. Orgmetra may consume a future released domain-neutral edge capability but must not copy mutable source/config or transfer product mapping/ACL authority to that owner.

### Keyverse and Orgmetra consumer ownership

Keyverse remains identity/issuer authority. Orgmetra subject-binding/consumer ACL and purpose-bound authorization owners remain separate. Product composition may perform request-scoped projection over released contracts but cannot widen the Keyverse claim model, infer Person identity directly from `sub`, cast caller-controlled organization/workspace fields into HRIS tenant identity, or make role/scope/purpose self-authorizing.

## Why the selected split follows the evidence

The Proposed direction remains **released shared edge transport when available + separately deployable Orgmetra product composition**. This is an ownership decision, not a claim that two network hops are intrinsically better. Generic transport already has a reusable owner; that owner does not own Orgmetra product semantics; protected Orgmetra architecture still requires a coherent product boundary; and HR/identity/authorization/idempotency/concurrency/retry truth already has narrower owners.

If measurement shows material overhead, optimization follows profiling of the complete deployed path rather than collapsing ownership or silently moving product semantics into the reverse proxy.

## Evidence discipline

A standards citation, repository file, open PR, architecture diagram, synthetic fixture, frozen dataclass, process-local registry, or local unit suite is not GREEN commercial evidence. Acceptance still requires exact protected/released identities, current-head conformance/security tests, independent review, immutable external authority evidence, explicit ACL projection tests, deployment-role least privilege, durable generation/activation/deployment/recovery evidence, fault injection, recovery/rollback evidence, and realistic k6/E2E measurements across every deployed layer and the owner PostgreSQL path.
