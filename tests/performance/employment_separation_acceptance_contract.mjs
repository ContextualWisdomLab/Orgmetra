import { createHash } from "node:crypto";
import { TextDecoder } from "node:util";

import { validatePerformanceFixture } from "./employment_separation_fixture_contract.mjs";
import { validatePerformanceLoadModel } from "./employment_separation_run_contract.mjs";

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

function sha256(value, label) {
  const text = stringValue(value, label).toLowerCase();
  if (!SHA256_PATTERN.test(text)) fail(`${label} must be a SHA-256 digest`);
  return text;
}

function reference(value, label) {
  const text = stringValue(value, label);
  if (text.length > 200 || !REFERENCE_PATTERN.test(text)) fail(`${label} must be a namespaced opaque reference`);
  return text;
}

function utcTimestamp(value, label) {
  const text = stringValue(value, label);
  if (!UTC_TIMESTAMP_PATTERN.test(text)) {
    fail(`${label} must be an RFC 3339 UTC timestamp`);
  }

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
  ) {
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

function rawBytes(value, label) {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  fail(`${label} must be supplied as raw bytes`);
}

function decodeStrictUtf8(value, label) {
  const bytes = rawBytes(value, label);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch (error) {
    throw new Error(`${label} must be valid UTF-8`, { cause: error });
  }
  if (text.trim() === "") fail(`${label} must be non-empty JSON text`);
  return { bytes, text };
}

function parseJsonArtifact(value, label) {
  const { bytes, text } = decodeStrictUtf8(value, label);
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    throw new Error(`${label} must be valid JSON`, { cause: error });
  }
  return {
    bytes,
    digest: createHash("sha256").update(bytes).digest("hex"),
    parsed,
  };
}

function metric(data, name) {
  const metrics = plainObject(data.k6, "result.k6").metrics;
  const table = plainObject(metrics, "result.k6.metrics");
  return plainObject(table[name], `result.k6.metrics.${name}`);
}

function metricValues(data, name) {
  return plainObject(metric(data, name).values, `result.k6.metrics.${name}.values`);
}

function sameLoadModel(observed, declared) {
  for (const field of [
    "executor",
    "target_rps",
    "duration_seconds",
    "preallocated_vus",
    "max_vus",
    "client_network_topology",
  ]) {
    if (observed[field] !== declared[field]) {
      fail(`runtime.observed_load_model.${field} must match result.load_model.${field}`);
    }
  }
}

function validateResult(result) {
  if (result.schema_version !== RESULT_SCHEMA) fail("result.schema_version is unsupported");
  const candidateSha = sha(result.candidate_sha, "result.candidate_sha");
  const fixtureSha256 = sha256(result.fixture_sha256, "result.fixture_sha256");
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
  const loadModel = validatePerformanceLoadModel(result.load_model, expectedIterations, profile);
  const completedIterations = nonNegativeInteger(result.completed_iterations, "result.completed_iterations");
  if (result.sample_complete !== true || completedIterations !== expectedIterations) {
    fail("result sample must be complete");
  }
  const completedAt = utcTimestamp(result.completed_at, "result.completed_at");

  const iterationValues = metricValues(result, "iterations");
  const metricIterations = nonNegativeInteger(iterationValues.count, "result.k6.metrics.iterations.values.count");
  if (metricIterations !== expectedIterations) fail("k6 iteration count must equal expected_iterations");

  const expectedLatencySamples = profile === "contention" ? expectedIterations * 2 : expectedIterations;
  if (!Number.isSafeInteger(expectedLatencySamples)) fail("expected latency sample count must be a safe integer");
  const latencySampleValues = metricValues(result, "employment_separation_latency_samples");
  const latencySampleCount = nonNegativeInteger(
    latencySampleValues.count,
    "result.k6.metrics.employment_separation_latency_samples.values.count",
  );
  if (latencySampleCount !== expectedLatencySamples) {
    fail(`latency sample count must equal ${expectedLatencySamples}`);
  }

  const checkValues = metricValues(result, "checks");
  if (finiteNumber(checkValues.rate, "result.k6.metrics.checks.values.rate", { maximum: 1 }) !== 1) {
    fail("k6 checks rate must equal 1");
  }
  const unexpectedValues = metricValues(result, "employment_separation_unexpected_response");
  if (finiteNumber(unexpectedValues.rate, "result.k6.metrics.employment_separation_unexpected_response.values.rate", { maximum: 1 }) !== 0) {
    fail("unexpected response rate must equal 0");
  }

  const trendValues = metricValues(result, trendName);
  const trendSampleCount = nonNegativeInteger(trendValues.count, `${trendName}.count`);
  if (trendSampleCount !== expectedLatencySamples) {
    fail(`Trend sample count must equal ${expectedLatencySamples}`);
  }
  const p50 = finiteNumber(trendValues["p(50)"], `${trendName}.p50`);
  const p95 = finiteNumber(trendValues["p(95)"], `${trendName}.p95`);
  const p99 = finiteNumber(trendValues["p(99)"], `${trendName}.p99`);
  const maximum = finiteNumber(trendValues.max, `${trendName}.max`);
  if (!(p50 <= p95 && p95 <= p99 && p99 <= maximum)) {
    fail(`${trendName} percentile evidence must be monotonic`);
  }
  if (profile === "first_commit" && p95 > 20) fail("first_commit p95 must be <= 20 ms");

  return { candidateSha, fixtureSha256, profile, p95, completedAt, expectedIterations, loadModel };
}

function parseAndValidateFixture(fixtureArtifact, result, validatedResult) {
  const fixtureDocument = parseJsonArtifact(fixtureArtifact, "performance fixture");
  if (fixtureDocument.digest !== validatedResult.fixtureSha256) {
    fail("result.fixture_sha256 does not bind the supplied performance fixture");
  }

  const fixture = validatePerformanceFixture(fixtureDocument.parsed, {
    minimumNonContendingRecords: MINIMUM_NON_CONTENDING_RECORDS,
    minimumContentionPairs: MINIMUM_CONTENTION_PAIRS,
  });
  if (fixture.candidate_sha.toLowerCase() !== validatedResult.candidateSha) {
    fail("fixture.candidate_sha must match result.candidate_sha");
  }
  for (const field of [
    "dataset_id",
    "clearance_reference",
    "preparation_protocol_reference",
    "prepared_state_evidence_reference",
    "resource_evidence_reference",
  ]) {
    if (fixture[field] !== result[field]) fail(`fixture.${field} must match result.${field}`);
  }
  for (const profileName of PROFILE_NAMES) {
    if (fixture.profile_preconditions[profileName] !== result.profile_preconditions[profileName]) {
      fail(`fixture.profile_preconditions.${profileName} must match result.profile_preconditions.${profileName}`);
    }
  }
  const expectedIterations = fixture.profiles[validatedResult.profile].length;
  if (expectedIterations !== result.expected_iterations) {
    fail("result.expected_iterations must equal the selected fixture profile cardinality");
  }
  return fixtureDocument.digest;
}

function validateRuntimeEvidence(runtime, resultDigest, result, validatedResult, fixtureDigest) {
  if (runtime.schema_version !== RUNTIME_SCHEMA) fail("runtime.schema_version is unsupported");
  const candidateSha = sha(runtime.candidate_sha, "runtime.candidate_sha");
  const observedServiceSha = sha(runtime.observed_service_sha, "runtime.observed_service_sha");
  if (candidateSha !== validatedResult.candidateSha) fail("runtime.candidate_sha must match result.candidate_sha");
  if (observedServiceSha !== validatedResult.candidateSha) fail("runtime.observed_service_sha must match candidate_sha");
  if (runtime.selected_profile !== validatedResult.profile) fail("runtime.selected_profile must match result.selected_profile");

  const suppliedDigest = sha256(runtime.performance_result_sha256, "runtime.performance_result_sha256");
  if (suppliedDigest !== resultDigest) fail("runtime.performance_result_sha256 does not bind the supplied result artifact");
  const runtimeFixtureDigest = sha256(runtime.fixture_sha256, "runtime.fixture_sha256");
  if (runtimeFixtureDigest !== fixtureDigest || runtimeFixtureDigest !== validatedResult.fixtureSha256) {
    fail("runtime.fixture_sha256 must match the exact validated performance fixture");
  }

  reference(runtime.environment_reference, "runtime.environment_reference");
  reference(runtime.deployment_reference, "runtime.deployment_reference");
  reference(runtime.observer_reference, "runtime.observer_reference");
  reference(runtime.load_observation_reference, "runtime.load_observation_reference");
  const observedLoadModel = validatePerformanceLoadModel(
    runtime.observed_load_model,
    validatedResult.expectedIterations,
    validatedResult.profile,
  );
  sameLoadModel(observedLoadModel, validatedResult.loadModel);
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

export function validateEmploymentSeparationAcceptance(resultArtifact, runtimeEvidence, fixtureArtifact) {
  const resultDocument = parseJsonArtifact(resultArtifact, "performance result");
  const result = plainObject(resultDocument.parsed, "result");
  const runtime = plainObject(runtimeEvidence, "runtime");
  const validatedResult = validateResult(result);
  const fixtureDigest = parseAndValidateFixture(fixtureArtifact, result, validatedResult);
  const resultDigest = validateRuntimeEvidence(
    runtime,
    resultDocument.digest,
    result,
    validatedResult,
    fixtureDigest,
  );
  return {
    structurally_valid: true,
    candidate_sha: validatedResult.candidateSha,
    selected_profile: validatedResult.profile,
    fixture_sha256: fixtureDigest,
    performance_result_sha256: resultDigest,
    p95_ms: validatedResult.p95,
  };
}
