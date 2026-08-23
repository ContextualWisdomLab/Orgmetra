# Document-record evidence traceability

## State

- **Protected-main truth:** `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` defines `document_records` as the owner of document metadata, source evidence and immutable artifact references, but has no executable document-record evidence package.
- **Active PR truth:** PR #98 adds a transport-neutral, value-minimized document metadata evidence contract. It is not protected-main/shipped truth until merged.
- **Out of scope:** document bytes/object-store implementation, Clearfolio/NewsDOM mutations, OCR, preview generation, legal retention decisions, content export, and employment-decision authority.

## Requirement → executable evidence

| Requirement | Evidence |
|---|---|
| Tenant, Person and Employment scope is explicit | `test_builds_value_minimized_document_evidence` plus malformed-reference regressions |
| Document content and HR values are not copied into canonical governance evidence | `test_builds_value_minimized_document_evidence` |
| Record identity and system-recorded time are Orgmetra-generated | `test_generates_packet_owned_reference_and_system_time` |
| Artifact, provenance and retention-policy integrity are SHA-256-bound | malformed digest regressions plus canonical digest assertion |
| Caller business receipt time remains distinct from system-recorded time | future/non-UTC receipt-time regressions |
| A valid-value rewrite after issuance cannot emit a second canonical truth | `test_rejects_valid_value_rewrite_after_issuance`; process-local creation digest is stored outside packet-writable slots and the verified payload snapshot is reused for export |
| Owned production statement and branch coverage are exact 100% | `Document Record Evidence Quality` workflow |
| Installed package, not source-tree import, is tested | exact-head hash-bound wheel build/install in `Document Record Evidence Quality` |

The process-local issuance digest is defense in depth only. It is not a durable signature, MAC key-management system, or substitute for database uniqueness/immutability. Durable evidence systems persist the already-emitted canonical bytes and digest through authoritative `document_records` and immutable `audit_provenance`/outbox persistence.

## Next authoritative boundary

Before any content read, export, disposition or high-impact HR action, the owning Orgmetra service must freshly re-resolve tenant, actor, purpose, resource, artifact digest/provenance, retention/legal-hold state and human authority, then write immutable audit/outbox evidence atomically with any consequential operation.
