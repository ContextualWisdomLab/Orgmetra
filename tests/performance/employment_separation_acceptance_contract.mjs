import { createHash } from "node:crypto";

const RESULT_SCHEMA = "orgmetra.employment_separation.performance_result.v1";
const RUNTIME_SCHEMA = "orgmetra.employment_separation.runtime_evidence.v1";
const SHA_PATTERN = /^[0-9a-f]{40}$/;
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const REFERENCE_PATTERN = /^[a-z][a-z0-9_]*:[A-Za-z0-9][A-Za-z0-9._~-]*$/;
const UTC_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const MINIMUM_NON_CONTENDING_RECORDS = 1000;
const MINIMUM_CONTENTION_PAIRS = 100;
const PROFILE_NAMES = Object.freeze(["first_commit", "replay", "rejection", "contention"]);
const PROFILE_PRECONDITIONS = Object.freeze({
  first_commit: "active_current_expected_version",
  replay: "same_key_same_semantics_already_committed",
  rejection: "expected_version_stale_or_semantic_conflict",
  contention: "active_current_expected_version",
});
const PROFILE_TRENDS = Object.freeze({
  first_commit: "employment_separation_first_commit_duration_ms",
  replay: "employment_separation_replay_duration_ms",
  rejection: "employment_separation_rejection_duration_ms",
  contention: "employment_separation_contention_duration_ms",
});
const RESIDUAL_FIELDS = Object.freeze([
  "residual_http_tasks",
  "residual_db_sessions",
  "residual_open_transactions",
  "residual_sockets",
  "residual_background_workers",
  "residual_pool_checkouts",
  "residual_pool_waiters",
]);

function fail(message) {
  throw new Error(message);
}

function plainObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} must be an object`);
  }
  return value;
}

function exactKeys(value, expected, label) {
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    fail(`${label} must contain exactly ${expected.join(", ")}`);
  }
}

function stringValue(value, label) {
  if (typeof value !== "string" || value.trim() === "") fail(`${label} must be a non-empty string`);
  return value;
}

function sha(value, label) {
  const text = stringValue(value, label).toLowerCase();
  if (!SHA_PATTERN.test(text)) fail(`${label} must be a full Git commit SHA`);
  return text;
}

function reference(value, label) {
  const text = stringValue(value, label);
  if (text.length > 200 || !REFERENCE_PATTERN.test(text)) fail(`${label} must be a namespaced opaque reference`);
  return text;
}

function utcTimestamp(value, label) {
  const text = stringValue(value, label);
  if (!UTC_TIMESTAMP_PATTERN.test(text) || Number.isNaN(Date.parse(text))) {
    fail(`${label} must be an RFC 3339 UTC timestamp`);
  }
  return text;
}

function positiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 1) fail(`${label} must be a positive safe integer`);
  return value;
}

function nonNegativeInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail(`${label} must be a non-negative safe integer`);
  return value;
}

function finiteNumber(value, label, { minimum = 0, maximum = Number.POSITIVE_INFINITY } = {}) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum) {
    fail(`${label} must be a finite number between ${minimum} and ${maximum}`);
  }
  return value;
}

function metric(data, name) {
  const metrics = plainObject(data.k6, "result.k6").metrics;
  const table = plainObject(metrics, "result.k6.metrics");
  return plainObject(table[name], `result.k6.metrics.${name}`);
}

function metricValues(data, name) {
  return plainObject(metric(data, name).values, `result.k6.metrics.${name}.values`);
}

function validateResult(result) {
  if (result.schema_version !== RESULT_SCHEMA) fail("result.schema_version is unsupported");
  const candidateSha = sha(result.candidate_sha, "result.candidate_sha");
  const profile = stringValue(result.selected_profile, "result.selected_profile");
  const trendName = PROFILE_TRENDS[profile];
  if (!trendName) fail("result.selected_profile is unsupported");

  reference(result.dataset_id, "result.dataset_id");
  reference(result.clearance_reference, "result.clearance_reference");
  reference(result.preparation_protocol_reference, "result.preparation_protocol_reference");
  reference(result.prepared_state_evidence_reference, "result.prepared_state_evidence_reference");
  reference(result.resource_evidence_reference, "result.resource_evidence_reference");
  const preconditions = plainObject(result.profile_preconditions, "result.profile_preconditions");
  exactKeys(preconditions, PROFILE_NAMES, "result.profile_preconditions");
  for (const profileName of PROFILE_NAMES) {
    if (preconditions[profileName] !== PROFILE_PRECONDITIONS[profileName]) {
      fail(`result.profile_preconditions.${profileName} must be ${PROFILE_PRECONDITIONS[profileName]}`);
    }
  }

  if (result.minimum_non_contending_records !== MINIMUM_NON_CONTENDING_RECORDS) {
    fail(`result.minimum_non_contending_records must equal ${MINIMUM_NON_CONTENDING_RECORDS}`);
  }
  if (result.minimum_contention_pairs !== MINIMUM_CONTENTION_PAIRS) {
    fail(`result.minimum_contention_pairs must equal ${MINIMUM_CONTENTION_PAIRS}`);
  }

  const expectedIterations = positiveInteger(result.expected_iterations, "result.expected_iterations");
  const minimumIterations = profile === "contention" ? MINIMUM_CONTENTION_PAIRS : MINIMUM_NON_CONTENDING_RECORDS;
  if (expectedIterations < minimumIterations) {
    fail(`${profile} requires at least ${minimumIterations} iterations`);
  }
  const completedIterations = nonNegativeInteger(result.completed_iterations, "result.completed_iterations");
  if (result.sample_complete !== true || completedIterations !== expectedIterations) {
    fail("result sample must be complete");
  }
  const completedAt = utcTimestamp(result.completed_at, "result.completed_at");

  const iterationValues = metricValues(result, "iterations");
  const metricIterations = nonNegativeInteger(iterationValues.count, "result.k6.metrics.iterations.values.count");
  if (metricIterations !== expectedIterations) fail("k6 iteration count must equal expected_iterations");

  const checkValues = metricValues(result, "checks");
  if (finiteNumber(checkValues.rate, "result.k6.metrics.checks.values.rate", { maximum: 1 }) !== 1) {
    fail("k6 checks rate must equal 1");
  }
  const unexpectedValues = metricValues(result, "employment_separation_unexpected_response");
  if (finiteNumber(unexpectedValues.rate, "result.k6.metrics.employment_separation_unexpected_response.values.rate", { maximum: 1 }) !== 0) {
    fail("unexpected response rate must equal 0");
  }

  const trendValues = metricValues(result, trendName);
  const p50 = finiteNumber(trendValues["p(50)"], `${trendName}.p50`);
  const p95 = finiteNumber(trendValues["p(95)"], `${trendName}.p95`);
  const p99 = finiteNumber(trendValues["p(99)"], `${trendName}.p99`);
  const maximum = finiteNumber(trendValues.max, `${trendName}.max`);
  if (!(p50 <= p95 && p95 <= p99 && p99 <= maximum)) {
    fail(`${trendName} percentile evidence must be monotonic`);
  }
  if (profile === "first_commit" && p95 > 20) fail("first_commit p95 must be <= 20 ms");

  return { candidateSha, profile, p95, completedAt };
}

function validateRuntimeEvidence(runtime, resultText, result, validatedResult) {
  if (runtime.schema_version !== RUNTIME_SCHEMA) fail("runtime.schema_version is unsupported");
  const candidateSha = sha(runtime.candidate_sha, "runtime.candidate_sha");
  const observedServiceSha = sha(runtime.observed_service_sha, "runtime.observed_service_sha");
  if (candidateSha !== validatedResult.candidateSha) fail("runtime.candidate_sha must match result.candidate_sha");
  if (observedServiceSha !== validatedResult.candidateSha) fail("runtime.observed_service_sha must match candidate_sha");
  if (runtime.selected_profile !== validatedResult.profile) fail("runtime.selected_profile must match result.selected_profile");

  const suppliedDigest = stringValue(runtime.performance_result_sha256, "runtime.performance_result_sha256").toLowerCase();
  if (!SHA256_PATTERN.test(suppliedDigest)) fail("runtime.performance_result_sha256 must be a SHA-256 digest");
  const observedDigest = createHash("sha256").update(resultText, "utf8").digest("hex");
  if (suppliedDigest !== observedDigest) fail("runtime.performance_result_sha256 does not bind the supplied result artifact");

  reference(runtime.environment_reference, "runtime.environment_reference");
  reference(runtime.deployment_reference, "runtime.deployment_reference");
  reference(runtime.observer_reference, "runtime.observer_reference");
  const resourceReference = reference(runtime.resource_evidence_reference, "runtime.resource_evidence_reference");
  if (resourceReference !== result.resource_evidence_reference) {
    fail("runtime.resource_evidence_reference must match result.resource_evidence_reference");
  }
  const observedAt = utcTimestamp(runtime.observed_at, "runtime.observed_at");
  if (Date.parse(observedAt) < Date.parse(validatedResult.completedAt)) {
    fail("runtime.observed_at must not precede result.completed_at");
  }

  finiteNumber(runtime.host_cpu_percent_p95, "runtime.host_cpu_percent_p95", { maximum: 100 });
  positiveInteger(runtime.host_rss_bytes_max, "runtime.host_rss_bytes_max");
  finiteNumber(runtime.db_pool_acquire_p95_ms, "runtime.db_pool_acquire_p95_ms");
  nonNegativeInteger(runtime.db_pool_in_use_max, "runtime.db_pool_in_use_max");
  nonNegativeInteger(runtime.db_pool_waiters_max, "runtime.db_pool_waiters_max");
  positiveInteger(runtime.db_connections_max, "runtime.db_connections_max");
  if (runtime.db_pool_in_use_max > runtime.db_connections_max) {
    fail("runtime.db_pool_in_use_max cannot exceed runtime.db_connections_max");
  }

  for (const field of RESIDUAL_FIELDS) {
    if (nonNegativeInteger(runtime[field], `runtime.${field}`) !== 0) {
      fail(`runtime.${field} must be 0`);
    }
  }

  return suppliedDigest;
}

export function validateEmploymentSeparationAcceptance(resultText, runtimeEvidence) {
  if (typeof resultText !== "string" || resultText.trim() === "") fail("performance result must be non-empty JSON text");
  let parsed;
  try {
    parsed = JSON.parse(resultText);
  } catch (error) {
    throw new Error("performance result must be valid JSON", { cause: error });
  }
  const result = plainObject(parsed, "result");
  const runtime = plainObject(runtimeEvidence, "runtime");
  const validatedResult = validateResult(result);
  const resultDigest = validateRuntimeEvidence(runtime, resultText, result, validatedResult);
  return {
    accepted: true,
    candidate_sha: validatedResult.candidateSha,
    selected_profile: validatedResult.profile,
    performance_result_sha256: resultDigest,
    p95_ms: validatedResult.p95,
  };
}
