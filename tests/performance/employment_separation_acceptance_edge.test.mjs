import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

const TREND_BY_PROFILE = {
  first_commit: "employment_separation_first_commit_duration_ms",
  replay: "employment_separation_replay_duration_ms",
  rejection: "employment_separation_rejection_duration_ms",
  contention: "employment_separation_contention_duration_ms",
};
const PROFILE_PRECONDITIONS = Object.freeze({
  first_commit: "active_current_expected_version",
  replay: "same_key_same_semantics_already_committed",
  rejection: "expected_version_stale_or_semantic_conflict",
  contention: "active_current_expected_version",
});
const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);

function result(profile = "first_commit") {
  const iterations = profile === "contention" ? 100 : 1000;
  const latencySamples = profile === "contention" ? iterations * 2 : iterations;
  const trend = profile === "first_commit"
    ? { "p(50)": 8, "p(95)": 18, "p(99)": 19, max: 22, count: latencySamples }
    : { "p(50)": 30, "p(95)": 80, "p(99)": 100, max: 120, count: latencySamples };
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: "a".repeat(40),
    fixture_sha256: FIXTURE_SHA256,
    selected_profile: profile,
    expected_iterations: iterations,
    completed_iterations: iterations,
    sample_complete: true,
    completed_at: "2026-09-13T04:10:00Z",
    load_model: acceptanceLoadModel(iterations),
    dataset_id: "dataset:employment-separation-perf-1",
    clearance_reference: "data_clearance:perf-2026-09",
    preparation_protocol_reference: "protocol:employment-separation-perf-v1",
    prepared_state_evidence_reference: "evidence:prepared-state-perf-1",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    profile_preconditions: { ...PROFILE_PRECONDITIONS },
    minimum_non_contending_records: 1000,
    minimum_contention_pairs: 100,
    k6: {
      metrics: {
        iterations: { values: { count: iterations } },
        dropped_iterations: { values: { count: 0 } },
        checks: { values: { rate: 1 } },
        employment_separation_unexpected_response: { values: { rate: 0 } },
        employment_separation_latency_samples: { values: { count: latencySamples } },
        [TREND_BY_PROFILE[profile]]: { values: trend },
      },
    },
  };
}

function runtime(resultArtifact, profile = "first_commit") {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: "a".repeat(40),
    observed_service_sha: "a".repeat(40),
    selected_profile: profile,
    performance_result_sha256: createHash("sha256").update(resultArtifact).digest("hex"),
    fixture_sha256: FIXTURE_SHA256,
    environment_reference: "environment:perf-staging-1",
    deployment_reference: "deployment:orgmetra-people-a1",
    observer_reference: "observer:perf-runtime-1",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    observed_at: "2026-09-13T04:10:01Z",
    host_cpu_percent_p95: 42,
    host_rss_bytes_max: 536870912,
    db_pool_acquire_p95_ms: 1,
    db_pool_in_use_max: 18,
    db_pool_waiters_max: 2,
    db_connections_max: 20,
    residual_http_tasks: 0,
    residual_db_sessions: 0,
    residual_open_transactions: 0,
    residual_sockets: 0,
    residual_background_workers: 0,
    residual_pool_checkouts: 0,
    residual_pool_waiters: 0,
  };
}

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function rejectResult(mutate, pattern = /./, profile = "first_commit") {
  const value = result(profile);
  mutate(value);
  const artifact = render(value);
  assert.throws(() => validateEmploymentSeparationAcceptance(artifact, runtime(artifact, profile), FIXTURE_BYTES), pattern);
}

function rejectRuntime(mutate, pattern = /./, profile = "first_commit") {
  const value = result(profile);
  const artifact = render(value);
  const evidence = runtime(artifact, profile);
  mutate(evidence);
  assert.throws(() => validateEmploymentSeparationAcceptance(artifact, evidence, FIXTURE_BYTES), pattern);
}

test("rejects malformed result and runtime containers", () => {
  assert.throws(() => validateEmploymentSeparationAcceptance("", {}, FIXTURE_BYTES), /raw bytes/);
  assert.throws(() => validateEmploymentSeparationAcceptance(4, {}, FIXTURE_BYTES), /raw bytes/);
  assert.throws(() => validateEmploymentSeparationAcceptance(Buffer.alloc(0), {}, FIXTURE_BYTES), /non-empty JSON text/);
  assert.throws(() => validateEmploymentSeparationAcceptance(Buffer.from("not json", "utf8"), {}, FIXTURE_BYTES), /valid JSON/);
  assert.throws(() => validateEmploymentSeparationAcceptance(Buffer.from("[]", "utf8"), {}, FIXTURE_BYTES), /result must be an object/);
  const artifact = render(result());
  assert.throws(() => validateEmploymentSeparationAcceptance(artifact, [], FIXTURE_BYTES), /runtime must be an object/);
  assert.throws(() => validateEmploymentSeparationAcceptance(artifact, null, FIXTURE_BYTES), /runtime must be an object/);
});

test("rejects invalid result authority and cardinality metadata", () => {
  rejectResult((value) => { value.schema_version = "v0"; }, /schema_version/);
  rejectResult((value) => { value.candidate_sha = ""; }, /non-empty string/);
  rejectResult((value) => { value.candidate_sha = "z".repeat(40); }, /full Git commit SHA/);
  rejectResult((value) => { value.fixture_sha256 = "bad"; }, /SHA-256 digest/);
  rejectResult((value) => { value.selected_profile = null; }, /non-empty string/);
  rejectResult((value) => { value.selected_profile = "unknown"; }, /unsupported/);
  rejectResult((value) => { value.minimum_non_contending_records = 999; }, /must equal 1000/);
  rejectResult((value) => { value.minimum_contention_pairs = 99; }, /must equal 100/);
  rejectResult((value) => { value.expected_iterations = 1.5; }, /positive safe integer/);
  rejectResult((value) => { value.expected_iterations = 0; }, /positive safe integer/);
  rejectResult((value) => { value.completed_iterations = 1.5; }, /non-negative safe integer/);
  rejectResult((value) => { value.completed_iterations = -1; }, /non-negative safe integer/);
  rejectResult((value) => { value.sample_complete = false; }, /sample must be complete/);
  rejectResult((value) => { value.completed_iterations = 999; }, /sample must be complete/);
});

test("rejects invalid load-model and client-network evidence", () => {
  rejectResult((value) => { delete value.load_model; }, /load_model must be an object/);
  rejectResult((value) => { value.load_model.executor = "shared-iterations"; }, /constant-arrival-rate/);
  rejectResult((value) => { value.load_model.duration_seconds = 999; }, /must equal expectedIterations exactly/);
  rejectResult((value) => { value.load_model.max_vus = 0; }, /positive safe integer/);
  rejectResult((value) => { value.load_model.client_network_topology = "https_mitm_proxy"; }, /client_network_topology/);
});

test("rejects invalid timestamps and result evidence references", () => {
  rejectResult((value) => { value.completed_at = "nope"; }, /UTC timestamp/);
  rejectResult((value) => { value.completed_at = "2026-13-40T04:10:00Z"; }, /UTC timestamp/);
  rejectResult((value) => { value.resource_evidence_reference = ""; }, /non-empty string/);
  rejectResult((value) => { value.resource_evidence_reference = "not namespaced"; }, /namespaced opaque reference/);
  rejectResult((value) => { value.resource_evidence_reference = `metrics:${"x".repeat(201)}`; }, /namespaced opaque reference/);
});

test("rejects malformed k6 metric containers and iteration evidence", () => {
  rejectResult((value) => { value.k6 = null; }, /result.k6 must be an object/);
  rejectResult((value) => { value.k6.metrics = []; }, /result.k6.metrics must be an object/);
  rejectResult((value) => { delete value.k6.metrics.iterations; }, /iterations must be an object/);
  rejectResult((value) => { value.k6.metrics.iterations.values = []; }, /iterations.values must be an object/);
  rejectResult((value) => { value.k6.metrics.iterations.values.count = 999; }, /iteration count/);
  rejectResult((value) => { delete value.k6.metrics.dropped_iterations; }, /dropped_iterations must be an object/);
  rejectResult((value) => { value.k6.metrics.dropped_iterations.values.count = 1; }, /dropped_iterations count must equal 0/);
  rejectResult((value) => { delete value.k6.metrics.employment_separation_latency_samples; }, /latency_samples must be an object/);
  rejectResult((value) => { value.k6.metrics.employment_separation_latency_samples.values.count = 999; }, /latency sample count/);
  rejectResult(
    (value) => { value.k6.metrics.employment_separation_latency_samples.values.count = 199; },
    /latency sample count/,
    "contention",
  );
  rejectResult((value) => { value.k6.metrics.employment_separation_first_commit_duration_ms.values.count = 999; }, /Trend sample count/);
  rejectResult(
    (value) => { value.k6.metrics.employment_separation_contention_duration_ms.values.count = 199; },
    /Trend sample count/,
    "contention",
  );
});

test("rejects invalid success and unexpected-response rates", () => {
  rejectResult((value) => { value.k6.metrics.checks.values.rate = 0.5; }, /checks rate must equal 1/);
  rejectResult((value) => { value.k6.metrics.checks.values.rate = "1"; }, /finite number/);
  rejectResult((value) => { value.k6.metrics.checks.values.rate = -0.1; }, /finite number/);
  rejectResult((value) => { value.k6.metrics.checks.values.rate = 1.1; }, /finite number/);
  rejectResult((value) => { value.k6.metrics.employment_separation_unexpected_response.values.rate = 0.1; }, /unexpected response rate/);
});

test("rejects invalid or non-monotonic latency distributions", () => {
  const metric = (value) => value.k6.metrics.employment_separation_first_commit_duration_ms.values;
  rejectResult((value) => { metric(value)["p(50)"] = null; }, /finite number/);
  rejectResult((value) => { metric(value)["p(50)"] = -1; }, /finite number/);
  rejectResult((value) => { metric(value)["p(50)"] = 19; metric(value)["p(95)"] = 18; }, /monotonic/);
  rejectResult((value) => { metric(value)["p(95)"] = 20; metric(value)["p(99)"] = 19; }, /monotonic/);
  rejectResult((value) => { metric(value)["p(99)"] = 23; metric(value).max = 22; }, /monotonic/);
});

test("accepts non-first profiles without applying the first-commit latency target", () => {
  for (const profile of ["replay", "rejection", "contention"]) {
    const value = result(profile);
    const artifact = render(value);
    const accepted = validateEmploymentSeparationAcceptance(artifact, runtime(artifact, profile), FIXTURE_BYTES);
    assert.equal(accepted.selected_profile, profile);
    assert.equal(accepted.p95_ms, 80);
  }
});

test("rejects malformed runtime authority and artifact binding", () => {
  rejectRuntime((value) => { value.schema_version = "v0"; }, /schema_version/);
  rejectRuntime((value) => { value.candidate_sha = "b".repeat(40); }, /candidate_sha must match/);
  rejectRuntime((value) => { value.candidate_sha = "bad"; }, /full Git commit SHA/);
  rejectRuntime((value) => { value.observed_service_sha = "b".repeat(40); }, /observed_service_sha/);
  rejectRuntime((value) => { value.observed_service_sha = "bad"; }, /full Git commit SHA/);
  rejectRuntime((value) => { value.selected_profile = "replay"; }, /selected_profile/);
  rejectRuntime((value) => { value.performance_result_sha256 = "bad"; }, /SHA-256 digest/);
  rejectRuntime((value) => { value.performance_result_sha256 = "0".repeat(64); }, /does not bind/);
  rejectRuntime((value) => { value.fixture_sha256 = "bad"; }, /SHA-256 digest/);
  rejectRuntime((value) => { value.fixture_sha256 = "0".repeat(64); }, /exact validated performance fixture/);
});

test("rejects invalid runtime references and observation time", () => {
  rejectRuntime((value) => { value.environment_reference = ""; }, /non-empty string/);
  rejectRuntime((value) => { value.environment_reference = "no namespace"; }, /namespaced opaque reference/);
  rejectRuntime((value) => { value.deployment_reference = "bad"; }, /namespaced opaque reference/);
  rejectRuntime((value) => { value.observer_reference = "bad"; }, /namespaced opaque reference/);
  rejectRuntime((value) => { value.resource_evidence_reference = "metrics:different"; }, /must match result.resource_evidence_reference/);
  rejectRuntime((value) => { value.observed_at = "nope"; }, /UTC timestamp/);
  rejectRuntime((value) => { value.observed_at = "2026-13-40T04:10:01Z"; }, /UTC timestamp/);
  rejectRuntime((value) => { value.observed_at = "2026-09-13T04:09:59Z"; }, /must not precede/);
});

test("rejects invalid host and pool measurements", () => {
  rejectRuntime((value) => { value.host_cpu_percent_p95 = "42"; }, /finite number/);
  rejectRuntime((value) => { value.host_cpu_percent_p95 = -1; }, /finite number/);
  rejectRuntime((value) => { value.host_cpu_percent_p95 = 101; }, /finite number/);
  rejectRuntime((value) => { value.host_rss_bytes_max = 0; }, /positive safe integer/);
  rejectRuntime((value) => { value.host_rss_bytes_max = 1.5; }, /positive safe integer/);
  rejectRuntime((value) => { value.db_pool_acquire_p95_ms = -1; }, /finite number/);
  rejectRuntime((value) => { value.db_pool_in_use_max = -1; }, /non-negative safe integer/);
  rejectRuntime((value) => { value.db_pool_in_use_max = 1.5; }, /non-negative safe integer/);
  rejectRuntime((value) => { value.db_pool_waiters_max = -1; }, /non-negative safe integer/);
  rejectRuntime((value) => { value.db_connections_max = 0; }, /positive safe integer/);
  rejectRuntime((value) => { value.db_pool_in_use_max = 21; }, /cannot exceed/);
});

test("rejects every residual resource and invalid residual counters", () => {
  const fields = [
    "residual_http_tasks",
    "residual_db_sessions",
    "residual_open_transactions",
    "residual_sockets",
    "residual_background_workers",
    "residual_pool_checkouts",
    "residual_pool_waiters",
  ];
  for (const field of fields) {
    rejectRuntime((value) => { value[field] = 1; }, new RegExp(`${field} must be 0`));
  }
  rejectRuntime((value) => { value.residual_http_tasks = -1; }, /non-negative safe integer/);
  rejectRuntime((value) => { value.residual_http_tasks = 1.5; }, /non-negative safe integer/);
});
