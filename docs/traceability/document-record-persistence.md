# Document-record persistence traceability

## Truth status

- Protected-main truth: `develop@9e3e4847510e1e612b48474ba42b177b8ed824df` has no `document_record` persistence relation.
- Dependency-active truth: PR #98 defines `DocumentRecordEvidence` and remains a separate dependency root.
- Active-PR truth: this stacked PR adds durable document metadata persistence only after #98's value boundary.
- Out of scope: document bytes/object storage, content viewing, export authorization, legal retention/disposition execution, employment decisions, and direct reads of People/audit/outbox application tables.

## Requirements → executable evidence

| Requirement | Implementation boundary | Regression evidence |
|---|---|---|
| Value minimization | `document_record` has metadata/references/digests plus the exact value-minimized canonical evidence JSON, never document content | test rejects prohibited value-bearing columns |
| Evidence-to-row binding | SHA-256 over exact stored canonical JSON; exact v1 key set/schema; typed-field equality; evidence receipt/issuance chronology | mismatch packet with a different valid evidence payload but predecessor digest must fail with `canonical evidence digest` |
| Person/Employment service extraction | opaque `person_record:` / `employment_record:` references | test rejects non-opaque Person reference and asserts no foreign FK to People tables |
| Audit/outbox service extraction | opaque `audit_event:` / `outbox_event:` references + application digest | test asserts no FK to audit/outbox application tables |
| Reviewed vocabulary | closed document category and fixed persistence purpose/reason | happy path + wrong-reason failure |
| Business/system time | caller `received_at`; evidence-issued `recorded_at` in canonical payload; PostgreSQL `transaction_timestamp()` durable `recorded_at` | future receipt, evidence chronology, and backdated persistence-time controls |
| Immutable metadata | UPDATE/DELETE/TRUNCATE guards | three destructive-operation failures |
| Tenant isolation | ENABLE + FORCE RLS with transaction tenant context and the shared tenant helper | NOSUPERUSER/NOBYPASSRLS reader sees only its tenant; no context sees zero rows; trigger functions pin the trusted search path |
| Non-decision posture | fixed classification/storage/decision-authority states | persisted-state assertion and canonical payload equality |
| Exact candidate provenance | pinned PostgreSQL workflow and exact-head checkout | `Document Record Persistence Quality` |

## Integration rule

This relation never authorizes foreign-resource use. Before persistence or retrieval, the host resolves tenant/purpose authorization and foreign reference truth through the owning service's published package/API/event contract. The initial shared PostgreSQL cluster is not permission for direct cross-service application-table SQL.
