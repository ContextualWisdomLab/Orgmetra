import assert from "node:assert/strict";
import test from "node:test";

import {
  PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  PERFORMANCE_SUMMARY_TREND_STATS,
  approvedPerformanceLoadModel,
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

test("uses one version-controlled open arrival-rate model per profile", () => {
  assert.deepEqual(approvedPerformanceLoadModel("first_commit"), {
    executor: "constant-arrival-rate",
    target_rps: 20,
    duration_seconds: 50,
    preallocated_vus: 20,
    max_vus: 80,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  });
  assert.deepEqual(approvedPerformanceLoadModel("contention"), {
    executor: "constant-arrival-rate",
    target_rps: 10,
    duration_seconds: 10,
    preallocated_vus: 20,
    max_vus: 80,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  });
  assert.deepEqual(arrivalRateScenarioForPerformanceProfile("first_commit", {
    expectedIterations: 1000,
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

test("refuses fixture cardinality that does not exactly fit the approved schedule", () => {
  assert.throws(() => arrivalRateScenarioForPerformanceProfile("first_commit", {
    expectedIterations: 999,
  }), /must equal expectedIterations exactly/);
  assert.throws(() => arrivalRateScenarioForPerformanceProfile("contention", {
    expectedIterations: 99,
  }), /must equal expectedIterations exactly/);
});

test("binds result evidence to the exact approved profile load model", () => {
  const approved = approvedPerformanceLoadModel("first_commit");
  assert.deepEqual(validatePerformanceLoadModel(approved, 1000, "first_commit"), approved);
  assert.deepEqual(
    validatePerformanceLoadModel(approvedPerformanceLoadModel("replay"), 1000, "replay"),
    approvedPerformanceLoadModel("replay"),
  );
  assert.deepEqual(
    validatePerformanceLoadModel(approvedPerformanceLoadModel("rejection"), 1000, "rejection"),
    approvedPerformanceLoadModel("rejection"),
  );
  assert.throws(() => validatePerformanceLoadModel({
    ...approved,
    target_rps: 1,
    duration_seconds: 1000,
    preallocated_vus: 1,
    max_vus: 1,
  }, 1000, "first_commit"), /approved first_commit load model/);
  assert.throws(() => validatePerformanceLoadModel({
    ...approved,
    executor: "shared-iterations",
  }, 1000, "first_commit"), /constant-arrival-rate/);
});

test("refuses load-model validation without explicit profile identity", () => {
  assert.throws(
    () => validatePerformanceLoadModel(approvedPerformanceLoadModel("replay"), 1000),
    /profile/i,
  );
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

test("uses exact scheduled completion rather than a zero-sample dropped-iteration threshold", () => {
  assert.deepEqual(thresholdsForPerformanceProfile("first_commit", 1000), {
    employment_separation_unexpected_response: ["rate==0"],
    employment_separation_latency_samples: ["count>=1000"],
    checks: ["rate==1"],
    iterations: ["count>=1000"],
    employment_separation_first_commit_duration_ms: ["p(95)<=20"],
  });
  assert.deepEqual(thresholdsForPerformanceProfile("contention", 100), {
    employment_separation_unexpected_response: ["rate==0"],
    employment_separation_latency_samples: ["count>=200"],
    checks: ["rate==1"],
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
