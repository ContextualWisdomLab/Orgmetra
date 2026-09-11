# ADR 0107: Immutable document-record metadata persistence

## Status

Active PR architecture. This decision does not describe protected-`develop` truth until the stacked change is integrated.

## Context

Orgmetra architecture assigns `document_records` ownership of HR document metadata and immutable artifact references. PR #98 adds a value-minimized `DocumentRecordEvidence` value boundary but intentionally leaves durable persistence out of scope. The persistence layer must keep document content and unrelated HR values out of the database relation, retain tenant isolation, distinguish business receipt time from system-recorded time, and remain extractable as its own service.

`people_core`, `audit_provenance`, and `integration_hub` are separate bounded contexts. Therefore the document-record relation must not query or foreign-key their application tables merely because the initial modular deployment can share one PostgreSQL cluster. Cross-context identities remain opaque released-contract references.

A digest column by itself is insufficient evidence binding: a caller could otherwise persist typed metadata from one document together with a syntactically valid SHA-256 from a different `DocumentRecordEvidence` packet. Durable persistence therefore has to retain the exact value-minimized canonical evidence bytes and verify that their digest and semantic fields describe the same row.

Raw JSON uniqueness is a separate trust property. PostgreSQL `jsonb` normalization can collapse duplicate object keys before key-count and typed-field checks run, so a byte-level digest plus a post-normalization 17-key check is not enough to prove that the submitted canonical bytes represented one reviewed object. Duplicate-key evidence must fail closed before `jsonb` normalization.

A second representation gap remains even after unique-key validation: syntactically valid JSON with the same keys and values can carry different whitespace, key order, or timestamp text. If a caller recomputes SHA-256 over those alternate bytes, digest verification and normalized semantic equality both succeed even though the bytes were not emitted by the reviewed `DocumentRecordEvidence.canonical_json()` contract. Persistence therefore has to prove deterministic encoding identity, not only semantic equivalence plus a matching caller-supplied digest.

## Decision

Add one immutable `document_record` relation owned by the document-records boundary. It stores:

- one opaque tenant-local document correlation;
- opaque Person and Employment references rather than cross-service table identifiers;
- reviewed document category, uploader/persisting actor correlations, and immutable artifact reference;
- SHA-256 artifact, source-provenance, retention-policy, evidence, and application-evidence digests;
- the exact bounded canonical JSON emitted by the reviewed `DocumentRecordEvidence` schema;
- opaque audit/outbox handoff references from owner contracts;
- business `received_at` and PostgreSQL-owned persistence `recorded_at`;
- fixed `restricted_hr`, `artifact_reference_only`, and `not_authorized_for_employment_decision` states.

An insert is accepted only when the SHA-256 of the exact stored canonical JSON equals `evidence_digest_sha256`, the raw JSON is one object with unique keys, the normalized object has exactly the reviewed v1 key set, every trust-bearing evidence field equals the typed persistence column or fixed state, the schema version is `orgmetra.document_record_evidence.v1`, the evidence receipt timestamp equals the row receipt timestamp, and the evidence issuance timestamp falls between receipt and durable persistence.

Migration `0022_document_record_evidence_unique_keys.sql` enforces the pre-normalization unique-key object predicate. Migration `0023_document_record_canonical_encoding.sql` separately reconstructs the reviewed v1 byte representation from the already validated typed row plus canonical UTC evidence timestamps and requires exact string equality with the stored evidence. That check rejects alternate separator whitespace, key ordering, and equivalent-but-noncanonical timestamp text even when the caller recomputes a matching digest. The reconstruction mirrors the package contract `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True)` for the v1 ASCII-constrained value vocabulary; it is version-specific and must change only with an explicit evidence-schema/version change.

The canonical JSON is value-minimized metadata evidence, not document content. The relation stores no document bytes/title, free-form HR text, compensation, rating, credentials, or employment-decision output. UPDATE, DELETE, and TRUNCATE are rejected. Lifecycle disposition belongs to a separate governed relation rather than rewriting the immutable metadata snapshot.

Tenant isolation uses enabled and forced PostgreSQL row-level security. A missing tenant context yields no visible rows. The design deliberately keeps Person/Employment/audit/outbox as opaque references so later service extraction does not require changing the persistence contract.

The migrations execute under a transaction-local `public, pg_catalog` search path, pin each trusted trigger function to `pg_catalog, public, pg_temp`, and reuse the shared `public.current_tenant_record_id()` policy helper.

## Consequences

This is an evidence/metadata system of record, not object storage and not authorization to read, export, delete, or use the document in an employment decision. The host must resolve current authorization and foreign references through released owner contracts before persistence or retrieval. Audit/outbox references are correlations to owner-controlled immutable evidence; this relation does not directly query those foreign application tables.

The deterministic-byte check intentionally couples persistence to evidence schema version v1. That is preferable to accepting multiple byte identities for one reviewed fact: a future serializer/vocabulary change requires a new versioned persistence contract rather than silently broadening v1 acceptance.

Migration numbers `0021` through `0023` are reserved in this stacked branch only. After parent #98 integrates, this PR must be retargeted to fresh `develop`, migration ordering reconciled, and all PostgreSQL contracts admitted through the canonical repository Foundation path before review readiness. No feature-local workflow is restored for that purpose.
