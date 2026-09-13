import assert from "node:assert/strict";
import test from "node:test";

import {
  PERFORMANCE_SUMMARY_TREND_STATS,
  requirePerformanceProfile,
  thresholdsForPerformanceProfile,
} from "./employment_separation_run_contract.mjs";

test("requires one explicit performance profile per run", () => {
  for (const profile of ["first_commit", "replay", "rejection", "contention"]) {
    assert.equal(requirePerformanceProfile(profile), profile);
  }
  assert.throws(() => requirePerformanceProfile(""), /must be exactly one of/);
  assert.throws(() => requirePerformanceProfile("all"), /must be exactly one of/);
});

test("applies the commercial p95 threshold only to the ordinary first-commit profile", () => {
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
