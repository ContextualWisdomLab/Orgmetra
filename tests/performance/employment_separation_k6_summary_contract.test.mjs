import assert from "node:assert/strict";
import test from "node:test";

import { normalizeEmploymentSeparationK6Summary } from "./employment_separation_k6_summary_contract.mjs";

const TREND = "employment_separation_first_commit_duration_ms";
const STATS = ["p(50)", "p(95)", "p(99)", "max", "count"];

function legacySummary({ iterations = 1000, latencySamples = iterations, trendName = TREND } = {}) {
  return {
    root_group: { name: "", path: "", id: "", groups: [], checks: [] },
    options: { summaryTrendStats: [...STATS], summaryTimeUnit: "", noColor: true },
    state: { isStdOutTTY: false, isStdErrTTY: false, testRunDurationMs: 50000 },
    setup_data: null,
    metrics: {
      iterations: { type: "counter", contains: "default", values: { count: iterations, rate: 20 } },
      checks: { type: "rate", contains: "default", values: { rate: 1, passes: iterations, fails: 0 } },
      employment_separation_unexpected_response: {
        type: "rate", contains: "default", values: { rate: 0, passes: 0, fails: iterations },
      },
      employment_separation_latency_samples: {
        type: "counter", contains: "default", values: { count: latencySamples, rate: 20 },
      },
      [trendName]: {
        type: "trend",
        contains: "time",
        values: { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3, count: latencySamples },
      },
    },
  };
}

function machineReadableSummary() {
  return {
    version: "1.0.0",
    metadata: { generatedAt: "2026-09-15T11:00:00Z", k6Version: "2.2.0" },
    config: { execution: "local", script: "employment_separation_buyer_path.js", duration: 50 },
    results: {
      metrics: [{
        name: TREND,
        type: "trend",
        contains: "time",
        values: { avg: 10, max: 22.3, med: 8.1, min: 2.2, "p(90)": 16.2, "p(95)": 18.4 },
      }],
      checks: { metrics: [], results: [] },
    },
  };
}

test("normalizes the pinned k6 2.2 default handleSummary contract with configured commercial percentiles", () => {
  const normalized = normalizeEmploymentSeparationK6Summary(legacySummary(), {
    expectedK6Version: "2.2.0",
    trendName: TREND,
  });
  assert.deepEqual(normalized.metrics.iterations.values, { count: 1000 });
  assert.deepEqual(normalized.metrics.checks.values, { rate: 1, passes: 1000, fails: 0 });
  assert.deepEqual(normalized.metrics.employment_separation_unexpected_response.values, { rate: 0, passes: 0, fails: 1000 });
  assert.equal(normalized.metrics.employment_separation_latency_samples.values.count, 1000);
  assert.deepEqual(normalized.metrics[TREND].values, { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3, count: 1000 });
  assert.equal(normalized.summary_contract, "k6-legacy-handle-summary");
  assert.equal(normalized.summary_k6_version, "2.2.0");
});

test("rejects the real k6 2.2 machine-readable trend shape instead of fabricating p99 or count", () => {
  assert.throws(
    () => normalizeEmploymentSeparationK6Summary(machineReadableSummary(), { expectedK6Version: "2.2.0", trendName: TREND }),
    /cannot supply required p\(99\) and trend count evidence/i,
  );
});

test("rejects a legacy summary whose configured trend statistics do not match commercial evidence", () => {
  const summary = legacySummary();
  summary.options.summaryTrendStats = ["med", "p(95)", "max"];
  assert.throws(
    () => normalizeEmploymentSeparationK6Summary(summary, { expectedK6Version: "2.2.0", trendName: TREND }),
    /summaryTrendStats/i,
  );
});

test("preserves one contention verdict while retaining two latency samples", () => {
  const contentionTrend = "employment_separation_contention_duration_ms";
  const normalized = normalizeEmploymentSeparationK6Summary(
    legacySummary({ iterations: 100, latencySamples: 200, trendName: contentionTrend }),
    { expectedK6Version: "2.2.0", trendName: contentionTrend },
  );
  assert.deepEqual(normalized.metrics.checks.values, { rate: 1, passes: 100, fails: 0 });
  assert.deepEqual(normalized.metrics.employment_separation_unexpected_response.values, { rate: 0, passes: 0, fails: 100 });
  assert.equal(normalized.metrics.employment_separation_latency_samples.values.count, 200);
  assert.equal(normalized.metrics[contentionTrend].values.count, 200);
});
