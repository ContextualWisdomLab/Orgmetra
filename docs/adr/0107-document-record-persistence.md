# ADR 0107: Immutable document-record metadata persistence

## Status

Active PR architecture. This decision does not describe protected-`develop` truth until the stacked change is integrated.

## Context

Orgmetra architecture assigns `document_records` ownership of HR document metadata and immutable artifact references. PR #98 adds a value-minimized `DocumentRecordEvidence` value boundary but intentionally leaves durable persistence out of scope. The persistence layer must keep document content and unrelated HR values out of the database relation, retain tenant isolation, distinguish business receipt time from system-recorded time, and remain extractable as its own service.

`people_core`, `audit_provenance`, and `integration_hub` are separate bounded contexts. Therefore the document-record relation must not query or foreign-key their application tables merely because the initial modular deployment can share one PostgreSQL cluster. Cross-context identities remain opaque published-contract references.

## Decision

Add one immutable `document_record` relation owned by the document-records boundary. It stores:

- one opaque tenant-local document correlation;
- opaque Person and Employment references rather than cross-service table identifiers;
- reviewed document category, uploader/persisting actor correlations, and immutable artifact reference;
- SHA-256 artifact, source-provenance, retention-policy, evidence, and application-evidence digests;
- opaque audit/outbox handoff references from owner contracts;
- business `received_at` and PostgreSQL-owned `recorded_at`;
- fixed `restricted_hr`, `artifact_reference_only`, and `not_authorized_for_employment_decision` states.

The relation stores no document bytes/title, free-form HR text, compensation, rating, credentials, or employment-decision output. UPDATE, DELETE, and TRUNCATE are rejected. Lifecycle disposition belongs to a separate governed relation rather than rewriting the immutable metadata snapshot.

Tenant isolation uses enabled and forced PostgreSQL row-level security. A missing tenant context yields no visible rows. The design deliberately keeps Person/Employment/audit/outbox as opaque references so later service extraction does not require changing the persistence contract.

## Consequences

This is an evidence/metadata system of record, not object storage and not authorization to read, export, delete, or use the document in an employment decision. The host must resolve current authorization and foreign references through published owner contracts before persistence or retrieval. Audit/outbox references are correlations to owner-controlled immutable evidence; this relation does not directly query those foreign application tables.

Migration number `0021` is reserved in this stacked branch only. After parent #98 integrates, this PR must be retargeted to fresh `develop` and migration ordering reconciled before review readiness.
