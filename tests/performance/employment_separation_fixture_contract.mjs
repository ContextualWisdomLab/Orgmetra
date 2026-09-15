const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ACTOR_PATTERN = /^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const VERSION_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]*$/;
const SHA_PATTERN = /^[0-9a-f]{40}$/;
const BODY_KEYS = Object.freeze([
  "confirmation_reference",
  "employment_record_id",
  "evidence_reference",
  "evidence_version_code",
  "expected_employment_record_version_id",
  "person_record_id",
  "separation_effective_on",
  "separation_reason_code",
]);
const REASON_CODES = new Set([
  "voluntary_resignation",
  "retirement_transition",
  "fixed_term_completion",
  "position_elimination",
  "employer_initiated_separation",
]);
const PROFILE_NAMES = Object.freeze(["first_commit", "replay", "rejection", "contention"]);
const PROFILE_PRECONDITIONS = Object.freeze({
  first_commit: "active_current_expected_version",
  replay: "same_key_same_semantics_already_committed",
  rejection: "expected_version_stale_or_semantic_conflict",
  contention: "active_current_expected_version",
});
const MAXIMUM_NON_CONTENDING_RECORDS = 1000;
const MAXIMUM_CONTENTION_PAIRS = 100;

function fail(message) {
  throw new Error(message);
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function requirePlainObject(value, label) {
  if (!isPlainObject(value)) fail(`${label} must be an object`);
  return value;
}

function requireExactKeys(value, expected, label) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    fail(`${label} must contain exactly: ${wanted.join(", ")}`);
  }
}

function requireString(value, label) {
  if (typeof value !== "string" || value.trim() === "") fail(`${label} must be a non-empty string`);
  return value;
}

function requireNamespacedReference(value, label) {
  const text = requireString(value, label);
  if (text.length > 200 || !ACTOR_PATTERN.test(text)) fail(`${label} must be a namespaced opaque reference`);
  return text;
}

function requireFullDate(value, label) {
  const text = requireString(value, label);
  if (!DATE_PATTERN.test(text)) fail(`${label} must be an RFC 3339 full-date`);
  const [year, month, day] = text.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year
    || parsed.getUTCMonth() !== month - 1
    || parsed.getUTCDate() !== day
  ) fail(`${label} must be an RFC 3339 full-date`);
  return text;
}

function requireUtcTimestamp(value, label) {
  const text = requireString(value, label);
  if (!UTC_TIMESTAMP_PATTERN.test(text)) fail(`${label} must be an RFC 3339 UTC timestamp`);
  const year = Number(text.slice(0, 4));
  const month = Number(text.slice(5, 7));
  const day = Number(text.slice(8, 10));
  const hour = Number(text.slice(11, 13));
  const minute = Number(text.slice(14, 16));
  const second = Number(text.slice(17, 19));
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (
    month < 1
    || month > 12
    || day < 1
    || day > daysInMonth[month - 1]
    || hour > 23
    || minute > 59
    || second > 59
  ) fail(`${label} must be an RFC 3339 UTC timestamp`);
  return text;
}

function requireUuid(value, label) {
  const text = requireString(value, label);
  if (!UUID_PATTERN.test(text)) fail(`${label} must be a canonical UUID string`);
  const compact = text.split("-").join("").toLowerCase();
  if (compact === "0".repeat(32) || compact === "f".repeat(32)) fail(`${label} must be an operational UUID`);
  return text.toLowerCase();
}

function requireCommand(command, label) {
  const value = requirePlainObject(command, label);
  requireExactKeys(value, ["actor_reference", "idempotency_key", "payload", "tenant_record_id"], label);
  requireUuid(value.tenant_record_id, `${label}.tenant_record_id`);
  requireNamespacedReference(value.actor_reference, `${label}.actor_reference`);
  const key = requireString(value.idempotency_key, `${label}.idempotency_key`);
  if (key.length < 16 || key.length > 200 || [...key].some((character) => {
    const code = character.charCodeAt(0);
    return code < 0x21 || code > 0x7e;
  })) {
    fail(`${label}.idempotency_key must be 16 to 200 visible ASCII characters`);
  }

  const payload = requirePlainObject(value.payload, `${label}.payload`);
  requireExactKeys(payload, BODY_KEYS, `${label}.payload`);
  requireUuid(payload.person_record_id, `${label}.payload.person_record_id`);
  requireUuid(payload.employment_record_id, `${label}.payload.employment_record_id`);
  requireUuid(payload.expected_employment_record_version_id, `${label}.payload.expected_employment_record_version_id`);
  requireFullDate(payload.separation_effective_on, `${label}.payload.separation_effective_on`);
  if (!REASON_CODES.has(payload.separation_reason_code)) {
    fail(`${label}.payload.separation_reason_code must use the governed vocabulary`);
  }
  requireNamespacedReference(payload.evidence_reference, `${label}.payload.evidence_reference`);
  const evidenceVersion = requireString(payload.evidence_version_code, `${label}.payload.evidence_version_code`);
  if (!VERSION_PATTERN.test(evidenceVersion)) fail(`${label}.payload.evidence_version_code must be a whitespace-free version token`);
  requireNamespacedReference(payload.confirmation_reference, `${label}.payload.confirmation_reference`);
  return value;
}

function semanticCommand(command) {
  return JSON.stringify({
    actor_reference: command.actor_reference,
    payload: command.payload,
    tenant_record_id: command.tenant_record_id,
  });
}

function recordIdentity(command) {
  return command.payload.employment_record_id.toLowerCase();
}

function reserveIdentity(seen, command, label) {
  const identity = recordIdentity(command);
  if (seen.has(identity)) fail(`${label} reuses an Employment assigned to another performance profile`);
  seen.add(identity);
}

export const PERFORMANCE_FIXTURE_SCHEMA = "orgmetra.employment_separation.performance_fixture.v1";

export function validatePerformanceFixture(
  document,
  { minimumNonContendingRecords = 1000, minimumContentionPairs = 100 } = {},
) {
  const fixture = requirePlainObject(document, "fixture");
  requireExactKeys(
    fixture,
    [
      "candidate_sha",
      "clearance_reference",
      "dataset_id",
      "prepared_at",
      "prepared_state_evidence_reference",
      "preparation_protocol_reference",
      "profile_preconditions",
      "profiles",
      "resource_evidence_reference",
      "right_cleared",
      "schema_version",
      "synthetic",
    ],
    "fixture",
  );
  if (fixture.schema_version !== PERFORMANCE_FIXTURE_SCHEMA) fail("fixture.schema_version is unsupported");
  if (fixture.right_cleared !== true) fail("fixture.right_cleared must be true for commercial acceptance");
  if (fixture.synthetic !== false) fail("fixture.synthetic must be false for commercial acceptance");
  requireNamespacedReference(fixture.clearance_reference, "fixture.clearance_reference");
  requireNamespacedReference(fixture.dataset_id, "fixture.dataset_id");
  requireNamespacedReference(fixture.preparation_protocol_reference, "fixture.preparation_protocol_reference");
  requireNamespacedReference(fixture.prepared_state_evidence_reference, "fixture.prepared_state_evidence_reference");
  requireNamespacedReference(fixture.resource_evidence_reference, "fixture.resource_evidence_reference");
  requireUtcTimestamp(fixture.prepared_at, "fixture.prepared_at");
  const candidateSha = requireString(fixture.candidate_sha, "fixture.candidate_sha").toLowerCase();
  if (!SHA_PATTERN.test(candidateSha)) fail("fixture.candidate_sha must be a full Git commit SHA");

  const preconditions = requirePlainObject(fixture.profile_preconditions, "fixture.profile_preconditions");
  requireExactKeys(preconditions, PROFILE_NAMES, "fixture.profile_preconditions");
  for (const profile of PROFILE_NAMES) {
    if (preconditions[profile] !== PROFILE_PRECONDITIONS[profile]) {
      fail(`fixture.profile_preconditions.${profile} must be ${PROFILE_PRECONDITIONS[profile]}`);
    }
  }

  const profiles = requirePlainObject(fixture.profiles, "fixture.profiles");
  requireExactKeys(profiles, PROFILE_NAMES, "fixture.profiles");
  for (const profile of ["first_commit", "replay", "rejection"]) {
    if (!Array.isArray(profiles[profile]) || profiles[profile].length < minimumNonContendingRecords) {
      fail(`fixture.profiles.${profile} must contain at least ${minimumNonContendingRecords} records`);
    }
    if (profiles[profile].length > MAXIMUM_NON_CONTENDING_RECORDS) {
      fail(`fixture.profiles.${profile} must contain at most ${MAXIMUM_NON_CONTENDING_RECORDS} records`);
    }
  }
  if (!Array.isArray(profiles.contention) || profiles.contention.length < minimumContentionPairs) {
    fail(`fixture.profiles.contention must contain at least ${minimumContentionPairs} pairs`);
  }
  if (profiles.contention.length > MAXIMUM_CONTENTION_PAIRS) {
    fail(`fixture.profiles.contention must contain at most ${MAXIMUM_CONTENTION_PAIRS} pairs`);
  }

  const seenEmployment = new Set();
  const seenKeys = new Set();
  for (const profile of ["first_commit", "replay", "rejection"]) {
    profiles[profile].forEach((raw, index) => {
      const label = `fixture.profiles.${profile}[${index}]`;
      const command = requireCommand(raw, label);
      reserveIdentity(seenEmployment, command, label);
      if (seenKeys.has(command.idempotency_key)) fail(`${label}.idempotency_key must be unique across fixture records`);
      seenKeys.add(command.idempotency_key);
    });
  }

  profiles.contention.forEach((raw, index) => {
    const label = `fixture.profiles.contention[${index}]`;
    const pair = requirePlainObject(raw, label);
    requireExactKeys(pair, ["left", "right"], label);
    const left = requireCommand(pair.left, `${label}.left`);
    const right = requireCommand(pair.right, `${label}.right`);
    if (left.idempotency_key === right.idempotency_key) fail(`${label} must use distinct idempotency keys`);
    if (semanticCommand(left) !== semanticCommand(right)) fail(`${label} commands must differ only by idempotency key`);
    reserveIdentity(seenEmployment, left, label);
    for (const command of [left, right]) {
      if (seenKeys.has(command.idempotency_key)) fail(`${label} idempotency keys must be unique across fixture records`);
      seenKeys.add(command.idempotency_key);
    }
  });

  return fixture;
}

export function requestHeaders(command, bearerToken) {
  requireCommand(command, "command");
  const token = requireString(bearerToken, "bearer token");
  if (token.length > 8192 || [...token].some((character) => {
    const code = character.charCodeAt(0);
    return code < 0x21 || code > 0x7e;
  })) fail("bearer token must be 1 to 8192 visible ASCII characters");
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "Idempotency-Key": command.idempotency_key,
    "X-Actor-Reference": command.actor_reference,
    "X-Purpose-Code": "workforce_admin",
    "X-Tenant-Reference": command.tenant_record_id,
  };
}

export function requestBody(command) {
  requireCommand(command, "command");
  return JSON.stringify(command.payload);
}