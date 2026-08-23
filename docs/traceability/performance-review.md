# Performance review traceability

Status: **active PR / proposed capability**, not protected-main truth.

| Requirement | Evidence | Status |
|---|---|---|
| Correlate review with Employment and Job references without claiming relationship resolution | `PerformanceReviewPacket.employment_record_reference`, `job_profile_reference`, fixed `scope_verification_state=requires_authoritative_resolution` | Implemented on active PR |
| Preserve authoritative tenant interoperability and packet-reference privacy | `test_authoritative_uuid7_tenant_identity_is_accepted_by_builder_and_replace`; `test_rejects_uuid1_trust_references_through_builder_and_replace` | `tenant_record_id` follows the canonical non-sentinel Orgmetra core operational-UUID contract; namespaced packet references require canonical non-sentinel UUIDv4 and reject UUIDv1/non-v4 suffixes through construction/replacement paths. |
| Require authoritative Person↔Employment↔Job/cycle/evidence resolution before rating | immutable scope-verification state plus governed `next_action` | Enforced as downstream prerequisite on active PR |
| Bind exact performance-cycle and business review period | `performance_cycle_reference`, `review_period_start`, `review_period_end` | Implemented on active PR |
| Bind predetermined criteria and goals | `criterion_set_reference`/digest, `goal_plan_reference`/digest | Implemented on active PR |
| Bind exact outcome evidence without copying values | `criterion_observation_snapshot_reference`/digest | Implemented on active PR |
| Preserve optional development provenance | paired `development_plan_reference`/digest | Implemented on active PR |
| Keep person PII, rating values, free-form feedback/model output outside packet | immutable false flags plus absence of value-bearing fields | Implemented on active PR |
| Require accountable human review | fixed `human_confirmation_required=True`, `decision_authority=human_review_only`, `review_state=requires_human_review` | Implemented on active PR |
| Version high-impact review evidence | bounded positive `evidence_version` is validated, serialized in canonical JSON, and changes SHA-256 correlation evidence | Implemented on active PR |
| Preserve deterministic system-recorded chronology without caller-owned timezone behavior | `generated_at` is resolved once to a built-in UTC instant at issuance; future instants, missing/raising offsets and normalization overflow fail closed; later canonical export accepts only that frozen UTC shape | `test_temporal_evidence_integrity.py` covers datetime subclasses, mutable/raising/missing timezone providers, future time, overflow, and post-construction non-UTC reinjection |
| Preserve deterministic immutable correlation evidence | canonical JSON plus SHA-256 | Implemented on active PR |
| Exact 100% owned statement/branch coverage | `packages/performance-review/pyproject.toml`, `.github/workflows/performance-review-quality.yml` | Required on exact PR head |
| Standards/research basis | ADR 0018; `docs/doctoring/performance-review-references.md` | Documented on active PR |

The packet does not persist or calculate a rating, decide compensation, infer performance, prove cross-record scope consistency, or prove scientific validity/fairness/compliance. UUIDv4 is an identifier-opacity constraint for packet-owned trust references only; tenant UUID generation/version/privacy policy remains owned by the authoritative HRIS boundary. Those claims require their own authoritative evidence and controls.
