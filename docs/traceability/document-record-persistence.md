# Document-record persistence traceability

## Truth status

- Protected truth: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f` has no `document_record` persistence relation.
- Dependency-active truth: PR #98 exact `ec39bfa9bcb73b2b7730a0a6115b2e484d78acb2` is the current `DocumentRecordEvidence` authority and has adopted protected `develop` without restoring retired feature-local workflows.
- Active-PR truth: PR #107 is a Draft child of #98. Its current branch preserves only the document-record persistence domain/docs/PostgreSQL contract delta on top of #98; obsolete persistence-local workflow and stale root Foundation/manifest registrations were intentionally not restacked.
- Out of scope: document bytes/object storage, content viewing, export authorization, legal retention/disposition execution, employment decisions, and direct reads of People/audit/outbox application tables. Completion-receipt and recovery-aware deletion authority remains downstream #308.

## Requirements → executable evidence

| Requirement | Implementation boundary | Regression evidence |
|---|---|---|
| Value minimization | `document_record` has metadata/references/digests plus the exact value-minimized canonical evidence JSON, never document content | `test_document_record_persistence_postgres.sh` rejects prohibited value-bearing columns |
| Evidence-to-row binding | SHA-256 over exact stored canonical JSON; exact v1 key set/schema; typed-field equality; evidence receipt/issuance chronology | mismatch packet with a different valid evidence payload but predecessor digest must fail with `canonical evidence digest` |
| Canonical JSON object integrity | migration `0022_document_record_evidence_unique_keys.sql` requires `canonical_evidence_json IS JSON OBJECT WITH UNIQUE KEYS` before `jsonb` normalization can collapse duplicate keys | `test_document_record_evidence_unique_keys_postgres.sh` recomputes SHA-256 over a syntactically valid duplicate-key payload and requires fail-closed rejection |
| Person/Employment service extraction | opaque `person_record:` / `employment_record:` references | test rejects non-opaque Person reference and asserts no foreign FK to People tables |
| Audit/outbox service extraction | opaque `audit_event:` / `outbox_event:` references + application digest | test asserts no FK to audit/outbox application tables |
| Reviewed vocabulary | closed document category and fixed persistence purpose/reason | happy path + wrong-reason failure |
| Business/system time | caller `received_at`; evidence-issued `recorded_at` in canonical payload; PostgreSQL `transaction_timestamp()` durable `recorded_at` | future receipt, evidence chronology, and backdated persistence-time controls |
| Immutable metadata | UPDATE/DELETE/TRUNCATE guards | three destructive-operation failures |
| Tenant isolation | ENABLE + FORCE RLS with transaction tenant context and the shared tenant helper | NOSUPERUSER/NOBYPASSRLS reader sees only its tenant; no context sees zero rows; trigger functions pin the trusted search path |
| Non-decision posture | fixed classification/storage/decision-authority states | persisted-state assertion and canonical payload equality |
| Repository-owned acceptance | #161 keeps Foundation as the canonical repository quality owner; #258/#259 owns package-neutral Foundation evolution | no exact-head hosted GREEN is claimed for this stacked child until canonical Foundation discovers and runs owned PostgreSQL contracts without restoring a feature-local workflow |

## Integration rule

This relation never authorizes foreign-resource use. Before persistence or retrieval, the host resolves tenant/purpose authorization and foreign reference truth through the owning service's released package/API/event contract. The shared PostgreSQL cluster is not permission for direct cross-service application-table SQL.

The #107 branch must remain Draft until current #98 authority and the canonical Foundation owner can produce fresh exact-head, non-vacuous PostgreSQL acceptance. Historical feature-local workflow results and predecessor heads are RCA only and do not transfer.
