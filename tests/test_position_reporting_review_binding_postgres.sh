#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:=postgresql://orgmetra:orgmetra@localhost:5432/orgmetra}"
TENANT_ID="10000000-0000-7000-8000-000000000001"
RELATIONSHIP_VERSION_ID="00000000-0000-7000-8000-000000000042"

binding="$(PGOPTIONS="-c orgmetra.tenant_record_id=${TENANT_ID}" \
    psql "${DATABASE_URL}" -Atqc "
SELECT
    version.review_evidence_digest_sha256 || '|' ||
    (audit.canonical_event_json::jsonb ->> 'orgmetraevidence')
FROM position_reporting_relationship_version AS version
JOIN audit_event_record AS audit
  ON audit.tenant_record_id = version.tenant_record_id
 AND audit.audit_event_record_id = version.audit_event_record_id
WHERE version.tenant_record_id = '${TENANT_ID}'::uuid
  AND version.position_reporting_relationship_version_id = '${RELATIONSHIP_VERSION_ID}'::uuid;
")"

review_digest="${binding%%|*}"
audit_evidence="${binding#*|}"
if [[ -z "${review_digest}" || "${review_digest}" != "${audit_evidence}" ]]; then
    echo "position-reporting review evidence is not bound into immutable application audit evidence: ${binding}" >&2
    exit 1
fi

echo "position-reporting immutable review-evidence binding passed"
