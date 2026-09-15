import assert from "node:assert/strict";
import test from "node:test";

import { normalizeEmploymentSeparationK6V2Summary } from "./employment_separation_k6_v2_summary_contract.mjs";

const TREND = "employment_separation_first_commit_duration_ms";

function counter(name, count) {
  return { name, type: "counter", contains: "default", values: { count } };
}

function rate(name, matches, total) {
  return { name, type: "rate", contains: "default", values: { matches, total, rate: total === 0 ? 0 : matches / total } };
}

function trend(name, count) {
  return {
    name,
    type: "trend",
    contains: "time",
    values: { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3, count },
  };
}

function summary({ iterations = 1000, latencySamples = iterations, trendName = TREND } = {}) {
  return {
    version: "1.0.0",
    metadata: { generatedAt: "2026-09-15T11:00:00Z", k6Version: "2.2.0" },
    config: { execution: "local", script: "employment_separation_buyer_path.js", duration: 50 },
    results: {
      metrics: [
        counter("iterations", iterations),
        rate("employment_separation_unexpected_response", 0, iterations),
        counter("employment_separation_latency_samples", latencySamples),
        trend(trendName, latencySamples),
      ],
      checks: {
        metrics: [
          counter("checks_total", iterations),
          rate("checks_succeeded", iterations, iterations),
          rate("checks_failed", 0, iterations),
        ],
        results: [],
      },
    },
  };
}

test("normalizes the pinned k6 v2 machine-readable summary into stable buyer evidence", () => {
  const normalized = normalizeEmploymentSeparationK6V2Summary(summary(), {
    expectedK6Version: "2.2.0",
    trendName: TREND,
  });

  assert.deepEqual(normalized.metrics.iterations.values, { count: 1000 });
  assert.deepEqual(normalized.metrics.checks.values, { rate: 1, passes: 1000, fails: 0 });
  assert.deepEqual(normalized.metrics.employment_separation_unexpected_response.values, {
    rate: 0,
    passes: 0,
    fails: 1000,
  });
  assert.equal(normalized.metrics.employment_separation_latency_samples.values.count, 1000);
  assert.equal(normalized.metrics[TREND].values.count, 1000);
  assert.equal(normalized.summary_version, "1.0.0");
  assert.equal(normalized.summary_k6_version, "2.2.0");
});

test("preserves one governed contention verdict while retaining two latency samples", () => {
  const contentionTrend = "employment_separation_contention_duration_ms";
  const normalized = normalizeEmploymentSeparationK6V2Summary(
    summary({ iterations: 100, latencySamples: 200, trendName: contentionTrend }),
    { expectedK6Version: "2.2.0", trendName: contentionTrend },
  );

  assert.deepEqual(normalized.metrics.checks.values, { rate: 1, passes: 100, fails: 0 });
  assert.deepEqual(normalized.metrics.employment_separation_unexpected_response.values, {
    rate: 0,
    passes: 0,
    fails: 100,
  });
  assert.equal(normalized.metrics.employment_separation_latency_samples.values.count, 200);
  assert.equal(normalized.metrics[contentionTrend].values.count, 200);
});

test("rejects unsupported summary and runtime versions", () => {
  const wrongSummary = summary();
  wrongSummary.version = "0.1.0";
  assert.throws(
    () => normalizeEmploymentSeparationK6V2Summary(wrongSummary, { expectedK6Version: "2.2.0", trendName: TREND }),
    /summary version/i,
  );

  const wrongRuntime = summary();
  wrongRuntime.metadata.k6Version = "2.1.0";
  assert.throws(
    () => normalizeEmploymentSeparationK6V2Summary(wrongRuntime, { expectedK6Version: "2.2.0", trendName: TREND }),
    /k6 version/i,
  );
});

test("rejects duplicate metric names before selecting commercial evidence", () => {
  const duplicate = summary();
  duplicate.results.metrics.push(counter("iterations", 1000));
  assert.throws(
    () => normalizeEmploymentSeparationK6V2Summary(duplicate, { expectedK6Version: "2.2.0", trendName: TREND }),
    /duplicate metric/i,
  );
});

test("rejects inconsistent check aggregate totals", () => {
  const inconsistent = summary();
  inconsistent.results.checks.metrics[1] = rate("checks_succeeded", 999, 1000);
  assert.throws(
    () => normalizeEmploymentSeparationK6V2Summary(inconsistent, { expectedK6Version: "2.2.0", trendName: TREND }),
    /check aggregate/i,
  );
});
