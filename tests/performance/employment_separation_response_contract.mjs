const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidUtcTimestamp(value) {
  if (typeof value !== "string" || !UTC_TIMESTAMP_PATTERN.test(value)) return false;
  const year = Number(value.slice(0, 4));
  const month = Number(value.slice(5, 7));
  const day = Number(value.slice(8, 10));
  const hour = Number(value.slice(11, 13));
  const minute = Number(value.slice(14, 16));
  const second = Number(value.slice(17, 19));
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return (
    month >= 1
    && month <= 12
    && day >= 1
    && day <= daysInMonth[month - 1]
    && hour <= 23
    && minute <= 59
    && second <= 59
  );
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
  if (!isValidUtcTimestamp(body.recorded_at)) return false;
  return body.replayed === replayed;
}

export function isGovernedSeparationConflict(status, body) {
  return status === 409 && isPlainObject(body) && body.error === "separation_conflict";
}