# API Contract

## Versioning

Orgmetra APIs use OpenAPI 3.2.0. Major versions are path-scoped under `/v1` until a breaking contract requires `/v2`.

## Command requirements

Every mutating request requires:

- `Idempotency-Key`
- tenant context
- actor context
- purpose code
- evidence references where the command is high-impact

## Example endpoints

```text
POST /v1/person-records
GET  /v1/person-records/{person_record_id}
POST /v1/employment-records
GET  /v1/employment-records/{employment_record_id}
POST /v1/job-profiles
POST /v1/job-profiles/{job_profile_id}/publish
POST /v1/candidate-profiles
POST /v1/selection-decisions
POST /v1/candidate-worker-links
POST /v1/criterion-observations
POST /v1/validity-studies
```

## Error shape

```json
{
  "error_code": "evidence_required",
  "message": "This decision requires at least one job-profile evidence reference.",
  "trace_id": "opaque_trace_reference",
  "details": {
    "missing_fields": ["evidence_reference"]
  }
}
```
