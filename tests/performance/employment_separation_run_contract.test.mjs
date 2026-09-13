import assert from "node:assert/strict";
import test from "node:test";

import {
  PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  PERFORMANCE_SUMMARY_TREND_STATS,
  arrivalRateScenarioForPerformanceProfile,
  requireDirectPerformanceClientNetwork,
  requirePerformanceProfile,
  thresholdsForPerformanceProfile,
  validatePerformanceLoadModel,
} from "./employment_separation_run_contract.mjs";

test("requires one explicit performance profile per run", () => {
  for (const profile of ["first_commit", "replay", "rejection", "contention"]) {
    assert.equal(requirePerformanceProfile(profile), profile);
  }
  assert.throws(() => requirePerformanceProfile(""), /must be exactly one of/);
  assert.throws(() => requirePerformanceProfile("all"), /must be exactly one of/);
});

test("uses an open arrival-rate model whose schedule is independent of response time", () => {
  assert.deepEqual(arrivalRateScenarioForPerformanceProfile("first_commit", {
    expectedIterations: 1000,
    targetRps: 20,
    durationSeconds: 50,
    preAllocatedVUs: 20,
    maxVUs: 80,
  }), {
    executor: "constant-arrival-rate",
    exec: "firstCommit",
    rate: 20,
    timeUnit: "1s",
    duration: "50s",
    preAllocatedVUs: 20,
    maxVUs: 80,
    gracefulStop: "30s",
  });
});

test("refuses arrival schedules that can hide load or outrun fixture cardinality", () => {
  assert.throws(() => arrivalRateScenarioForPerformanceProfile("first_commit", {
    expectedIterations: 1000,
    targetRps: 20,
    durationSeconds: 49,
    preAllocatedVUs: 20,
    maxVUs: 80,
  }), /must equal expectedIterations exactly/);
  assert.throws(() => arrivalRateScenarioForPerformanceProfile("contention", {
    expectedIterations: 100,
    targetRps: 10,
    durationSeconds: 10,
    preAllocatedVUs: 20,
    maxVUs: 10,
  }), /greater than or equal/);
});

test("binds result evidence to the exact open load model", () => {
  assert.deepEqual(validatePerformanceLoadModel({
    executor: "constant-arrival-rate",
    target_rps: 20,
    duration_seconds: 50,
    preallocated_vus: 20,
    max_vus: 80,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  }, 1000), {
    executor: "constant-arrival-rate",
    target_rps: 20,
    duration_seconds: 50,
    preallocated_vus: 20,
    max_vus: 80,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  });
  assert.throws(() => validatePerformanceLoadModel({
    executor: "shared-iterations",
    target_rps: 20,
    duration_seconds: 50,
    preallocated_vus: 20,
    max_vus: 80,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  }, 1000), /constant-arrival-rate/);
});

test("fails closed when the k6 client is routed through an ambient proxy", () => {
  assert.equal(requireDirectPerformanceClientNetwork({}), PERFORMANCE_CLIENT_NETWORK_TOPOLOGY);
  assert.throws(
    () => requireDirectPerformanceClientNetwork({ HTTPS_PROXY: "https://proxy.example" }),
    /HTTPS_PROXY must be unset/,
  );
  assert.throws(
    () => requireDirectPerformanceClientNetwork({ all_proxy: "socks5://proxy.example" }),
    /all_proxy must be unset/,
  );
});

test("applies the commercial p95 threshold only to the ordinary first-commit profile", () => {
  assert.deepEqual(thresholdsForPerformanceProfile("first_commit", 1000), {
    employment_separation_unexpected_response: ["rate==0"],
    employment_separation_latency_samples: ["count>=1000"],
    checks: ["rate==1"],
    dropped_iterations: ["count==0"],
    iterations: ["count>=1000"],
    employment_separation_first_commit_duration_ms: ["p(95)<=20"],
  });
  assert.deepEqual(thresholdsForPerformanceProfile("contention", 100), {
    employment_separation_unexpected_response: ["rate==0"],
    employment_separation_latency_samples: ["count>=200"],
    checks: ["rate==1"],
    dropped_iterations: ["count==0"],
    iterations: ["count>=100"],
  });
});

test("refuses acceptance thresholds without an exact positive iteration requirement", () => {
  assert.throws(() => thresholdsForPerformanceProfile("first_commit", 0), /positive safe integer/);
  assert.throws(() => thresholdsForPerformanceProfile("first_commit", 1.5), /positive safe integer/);
});

test("requires buyer percentiles plus the exact Trend sample count", () => {
  assert.deepEqual(PERFORMANCE_SUMMARY_TREND_STATS, ["p(50)", "p(95)", "p(99)", "max", "count"]);
});
