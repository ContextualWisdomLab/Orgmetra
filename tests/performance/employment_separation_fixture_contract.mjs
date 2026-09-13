const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ACTOR_PATTERN = /^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
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
  const actor = requireString(value.actor_reference, `${label}.actor_reference`);
  if (!ACTOR_PATTERN.test(actor)) fail(`${label}.actor_reference must be a namespaced opaque reference`);
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
  if (typeof payload.separation_effective_on !== "string" || !DATE_PATTERN.test(payload.separation_effective_on)) {
    fail(`${label}.payload.separation_effective_on must be an RFC 3339 full-date`);
  }
  if (!REASON_CODES.has(payload.separation_reason_code)) {
    fail(`${label}.payload.separation_reason_code must use the governed vocabulary`);
  }
  requireString(payload.evidence_reference, `${label}.payload.evidence_reference`);
  requireString(payload.evidence_version_code, `${label}.payload.evidence_version_code`);
  requireString(payload.confirmation_reference, `${label}.payload.confirmation_reference`);
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
  requireString(fixture.clearance_reference, "fixture.clearance_reference");
  requireString(fixture.dataset_id, "fixture.dataset_id");
  requireString(fixture.prepared_at, "fixture.prepared_at");
  requireString(fixture.resource_evidence_reference, "fixture.resource_evidence_reference");
  const candidateSha = requireString(fixture.candidate_sha, "fixture.candidate_sha").toLowerCase();
  if (!SHA_PATTERN.test(candidateSha)) fail("fixture.candidate_sha must be a full Git commit SHA");

  const profiles = requirePlainObject(fixture.profiles, "fixture.profiles");
  requireExactKeys(profiles, PROFILE_NAMES, "fixture.profiles");
  for (const profile of ["first_commit", "replay", "rejection"]) {
    if (!Array.isArray(profiles[profile]) || profiles[profile].length < minimumNonContendingRecords) {
      fail(`fixture.profiles.${profile} must contain at least ${minimumNonContendingRecords} records`);
    }
  }
  if (!Array.isArray(profiles.contention) || profiles.contention.length < minimumContentionPairs) {
    fail(`fixture.profiles.contention must contain at least ${minimumContentionPairs} pairs`);
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
