const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function isGovernedSeparationSuccess(status, body, { employmentRecordId, replayed }) {
  if (status !== 200 || !isPlainObject(body)) return false;
  if (typeof employmentRecordId !== "string" || !UUID_PATTERN.test(employmentRecordId)) return false;
  if (typeof replayed !== "boolean") return false;
  if (typeof body.employment_record_id !== "string" || body.employment_record_id.toLowerCase() !== employmentRecordId.toLowerCase()) {
    return false;
  }
  if (typeof body.separated_employment_record_version_id !== "string" || !UUID_PATTERN.test(body.separated_employment_record_version_id)) {
    return false;
  }
  if (typeof body.recorded_at !== "string" || !UTC_TIMESTAMP_PATTERN.test(body.recorded_at) || Number.isNaN(Date.parse(body.recorded_at))) {
    return false;
  }
  return body.replayed === replayed;
}

export function isGovernedSeparationConflict(status, body) {
  return status === 409 && isPlainObject(body) && body.error === "separation_conflict";
}
