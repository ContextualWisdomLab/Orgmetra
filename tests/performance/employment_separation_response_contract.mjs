import { parseStrictJsonText } from "./strict_json_artifact.mjs";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/;
const SUPPORT_REFERENCE_PATTERN = /^err_[A-Za-z0-9_-]{32}$/;
const HTTP_TOKEN_PATTERN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/u;
const MAXIMUM_GOVERNED_RESPONSE_BODY_BYTES = 16 * 1024;
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
    year >= 1
    && year <= 9999
    && month >= 1
    && month <= 12
    && day >= 1
    && day <= daysInMonth[month - 1]
    && hour <= 23
    && minute <= 59
    && second <= 59
  );
}

function splitContentTypeSegments(value) {
  const segments = [];
  let start = 0;
  let quoted = false;
  let escaped = false;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (escaped) {
      const codePoint = character.codePointAt(0);
      if (codePoint !== 0x09 && (codePoint < 0x20 || codePoint === 0x7f)) return null;
      escaped = false;
      continue;
    }
    if (quoted) {
      if (character === "\\") {
        escaped = true;
      } else if (character === '"') {
        quoted = false;
      } else {
        const codePoint = character.codePointAt(0);
        if (codePoint !== 0x09 && (codePoint < 0x20 || codePoint === 0x7f)) return null;
      }
      continue;
    }
    if (character === '"') {
      quoted = true;
      continue;
    }
    if (character === ",") return null;
    if (character === ";") {
      segments.push(value.slice(start, index));
      start = index + 1;
    }
  }
  if (quoted || escaped) return null;
  segments.push(value.slice(start));
  return segments;
}

function isValidQuotedParameterValue(value) {
  if (value.length < 2 || value[0] !== '"' || value[value.length - 1] !== '"') return false;
  let escaped = false;
  for (let index = 1; index < value.length - 1; index += 1) {
    const character = value[index];
    const codePoint = character.codePointAt(0);
    if (escaped) {
      if (codePoint !== 0x09 && (codePoint < 0x20 || codePoint === 0x7f)) return false;
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      continue;
    }
    if (character === '"') return false;
    if (codePoint !== 0x09 && (codePoint < 0x20 || codePoint === 0x7f)) return false;
  }
  return !escaped;
}

function parseContentTypeParameter(segment) {
  const text = segment.trim();
  const separator = text.indexOf("=");
  if (separator <= 0) return null;
  const rawName = text.slice(0, separator);
  const rawValue = text.slice(separator + 1);
  if (rawName !== rawName.trim() || rawValue !== rawValue.trim()) return null;
  if (!HTTP_TOKEN_PATTERN.test(rawName) || rawValue === "") return null;
  if (!HTTP_TOKEN_PATTERN.test(rawValue) && !isValidQuotedParameterValue(rawValue)) return null;
  return rawName.toLowerCase();
}

function exceedsUtf8ByteBudget(value, maximumBytes) {
  let bytes = 0;
  for (const character of value) {
    const codePoint = character.codePointAt(0);
    if (codePoint <= 0x7f) bytes += 1;
    else if (codePoint <= 0x7ff) bytes += 2;
    else if (codePoint <= 0xffff) bytes += 3;
    else bytes += 4;
    if (bytes > maximumBytes) return true;
  }
  return false;
}

export function hasGovernedSeparationJsonMediaType(headers) {
  if (!isPlainObject(headers)) return false;
  const contentTypeEntries = Object.entries(headers).filter(
    ([name]) => name.toLowerCase() === "content-type",
  );
  if (contentTypeEntries.length !== 1) return false;
  const value = contentTypeEntries[0][1];
  if (typeof value !== "string") return false;
  const segments = splitContentTypeSegments(value);
  if (segments === null || segments.length < 1) return false;
  const mediaType = segments[0].trim().toLowerCase();
  if (mediaType !== "application/json") return false;
  const parameterNames = new Set();
  for (const segment of segments.slice(1)) {
    const parameterName = parseContentTypeParameter(segment);
    if (parameterName === null || parameterNames.has(parameterName)) return false;
    parameterNames.add(parameterName);
  }
  return true;
}

export function parseGovernedSeparationResponseBody(value) {
  if (typeof value !== "string") {
    throw new Error("governed separation response body must be JSON text");
  }
  if (exceedsUtf8ByteBudget(value, MAXIMUM_GOVERNED_RESPONSE_BODY_BYTES)) {
    throw new Error(
      `governed separation response body must not exceed ${MAXIMUM_GOVERNED_RESPONSE_BODY_BYTES} UTF-8 bytes`,
    );
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
