import { parseStrictJsonText } from "./strict_json_artifact.mjs";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const SUPPORT_REFERENCE_PATTERN = /^err_[A-Za-z0-9_-]{20,80}$/;
const SUCCESS_RESPONSE_KEYS = Object.freeze([
  "employment_record_id",
  "separated_employment_record_version_id",
  "recorded_at",
  "replayed",
]);
const ERROR_RESPONSE_KEYS = Object.freeze([
  "error_code",
  "message",
  "next_action",
  "support_reference",
]);

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value, expectedKeys) {
  const actual = Object.keys(value).sort();
  const expected = [...expectedKeys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function isOperationalUuid(value) {
  if (typeof value !== "string" || !UUID_PATTERN.test(value)) return false;
  const compact = value.replaceAll("-", "").toLowerCase();
  return compact !== "0".repeat(32) && compact !== "f".repeat(32);
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

export function parseGovernedSeparationResponseBody(value) {
  if (typeof value !== "string") {
    throw new Error("governed separation response body must be JSON text");
  }
  return parseStrictJsonText(value, "governed separation response body");
}

export function isGovernedSeparationSuccess(status, body, { employmentRecordId, replayed }) {
  if (status !== 200 || !isPlainObject(body) || !hasExactKeys(body, SUCCESS_RESPONSE_KEYS)) return false;
  if (!isOperationalUuid(employmentRecordId)) return false;
  if (typeof replayed !== "boolean") return false;
  if (!isOperationalUuid(body.employment_record_id) || body.employment_record_id.toLowerCase() !== employmentRecordId.toLowerCase()) {
    return false;
  }
  if (!isOperationalUuid(body.separated_employment_record_version_id)) return false;
  if (!isValidUtcTimestamp(body.recorded_at)) return false;
  return body.replayed === replayed;
}

export function isGovernedSeparationConflict(status, body) {
  if (status !== 409 || !isPlainObject(body) || !hasExactKeys(body, ERROR_RESPONSE_KEYS)) return false;
  if (body.error_code !== "separation_conflict") return false;
  if (typeof body.message !== "string" || body.message.length < 1 || body.message.length > 1000) return false;
  if (typeof body.next_action !== "string" || body.next_action.length < 1 || body.next_action.length > 1000) return false;
  return typeof body.support_reference === "string" && SUPPORT_REFERENCE_PATTERN.test(body.support_reference);
}
