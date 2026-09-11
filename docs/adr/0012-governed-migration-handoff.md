# ADR 0012: Governed HRIS migration uses a value-free handoff envelope

## Status

Accepted on this active PR only. This is not protected-`develop` product truth until the owning PR integrates.

## Context

Orgmetra has an authoritative bitemporal HRIS core, but buyers also need a defensible path for migrating legacy HR data without turning an ETL tool into a shadow HR system or allowing a parsed export to become authoritative merely because it can be transformed.

The current published MHTML ETL Gateway contract at revision `779254927abb1e7cee80fd949907ccd03f9fc7be` exposes deterministic source SHA-256 identity and a value-free `SchemaProposal` containing a content-addressed proposal identifier and table fingerprint while keeping source headers and values inside the protected source-custody workflow. Its own contract explicitly leaves authorization, approval, transport, and persistence to the caller.

The current mightyETL `develop` contract at revision `ba8911f50ed20a39927a0d51c0cf20f9b7c91820` exposes bounded synchronous ETL batches that prevalidate the complete request before the first database write and execute accepted writes in one transaction. Orgmetra must consume that published boundary without copying mightyETL code, directly writing another service's tables, or claiming stronger execution semantics than the owner publishes.

W3C PROV-DM treats provenance as evidence about entities, activities, and responsible agents involved in producing data. NIST SP 800-53 Rev. 5, including the current Release 5.2.0 update notice, retains information-integrity controls relevant to detecting and protecting against unauthorized changes. Orgmetra uses those public principles as design traceability, not as a certification claim.

## Decision

Orgmetra introduces a transport-neutral `orgmetra-migration-adapter` package that builds one deterministic pre-write handoff envelope.

The envelope:

- requires an operational tenant UUID, namespaced migration-batch reference, accountable actor, explicit approval reference, purpose and reason;
- requires the boolean singleton `True` for human confirmation;
- binds the exact MHTML source SHA-256, source byte count, value-free schema proposal ID, table fingerprint, and an Orgmetra-owned approved mapping digest;
- pins the exact reviewed MHTML ETL Gateway and mightyETL revisions and fails closed on dependency drift;
- permits only the authoritative HRIS core object families: Person, Employment, Organization, Job, Position, and Assignment;
- canonicalizes target object codes and emits deterministic UTF-8 JSON plus SHA-256 evidence;
- limits one handoff to at most 1,000 records, matching the reviewed conservative mightyETL default batch bound rather than silently assuming a larger deployment-specific limit;
- contains no raw source header, source value, human-readable PII, provider credential, connection string, SQL, or cross-service database access;
- labels itself `value_free` and records `execution_mode="bounded_atomic_batch"` only as the requested/contracted mode for the subsequent mightyETL execution boundary, never as an observed result or evidence that an atomic migration completed;
- always sets `requires_reconciliation=true` and supplies a customer-facing next action that requires reconciliation before completion can be claimed.

Consumers MUST NOT interpret `execution_mode="bounded_atomic_batch"` as completion evidence. Completion and atomicity are established only by outcome evidence returned from the subsequent owner execution boundary and reconciled into Orgmetra's governed audit path.

This slice does not authenticate an operator, authorize access to the underlying source file, execute mightyETL, retry a batch, persist migration state, write HRIS rows, or declare a migration complete. Those are separate application and operator boundaries. A later execution slice must consume the exact owner contracts and bind the resulting outcome into Orgmetra's immutable audit/outbox evidence without duplicating foreign runtime behavior.

## Consequences

### Positive

- A source export cannot cross into the HRIS migration lane without exact source, schema, mapping, tenant, actor, approval, and purpose provenance.
- Dependency upgrades become explicit revalidation events instead of silently changing migration semantics.
- PII and raw source values stay out of the handoff evidence.
- The envelope is deterministic and can be correlated with immutable Orgmetra audit evidence without copying source content.
- Buyers receive an explicit next action rather than a misleading success state.
- Requested execution semantics remain distinct from observed execution outcomes, preventing a pre-write envelope from being misused as proof of migration completion.

### Costs and limitations

- The adapter intentionally blocks a newly revised foreign contract until Orgmetra revalidates and updates the exact revision pin.
- A 1,000-record handoff bound is conservative even when a mightyETL deployment permits a larger configured limit.
- This slice is a pre-write governance boundary, not a migration executor or reconciliation store.

## Verification

`packages/migration-adapter/tests/test_handoff.py` requires exact 100% owned statement and branch coverage. It covers deterministic canonicalization, exact SHA-256 derivation from canonical JSON, all supported HRIS object families, malformed or reserved tenant IDs, malformed governance references/codes, non-boolean human confirmation, digest/proposal errors, bounded-record enforcement, duplicate/unsupported targets, dependency-revision drift, direct-constructor invariant bypass attempts, immutability, and safe failure messages.

`.github/workflows/foundation-ci.yml` checks out the exact candidate SHA, installs the repository's reviewed hashed Python test toolchain once, compiles the package, runs the full package test suite with 100% statement/branch thresholds, and requires a clean checkout.
