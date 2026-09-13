import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";

function performanceResult(profile, iterations) {
  const trendName = profile === "contention"
    ? "employment_separation_contention_duration_ms"
    : "employment_separation_first_commit_duration_ms";
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: "a".repeat(40),
    selected_profile: profile,
    expected_iterations: iterations,
    completed_iterations: iterations,
    sample_complete: true,
    completed_at: "2026-09-13T04:10:00Z",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    minimum_non_contending_records: 1000,
    minimum_contention_pairs: 100,
    k6: {
      metrics: {
        iterations: { values: { count: iterations } },
        checks: { values: { rate: 1 } },
        employment_separation_unexpected_response: { values: { rate: 0 } },
        [trendName]: {
          values: profile === "contention"
            ? { "p(50)": 12, "p(95)": 80, "p(99)": 120, max: 200 }
            : { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3 },
        },
      },
    },
  };
}

function runtimeEvidence(resultText, profile) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: "a".repeat(40),
    observed_service_sha: "a".repeat(40),
    selected_profile: profile,
    performance_result_sha256: createHash("sha256").update(resultText, "utf8").digest("hex"),
    environment_reference: "environment:perf-staging-1",
    deployment_reference: "deployment:orgmetra-people-a1",
    observer_reference: "observer:perf-runtime-1",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    observed_at: "2026-09-13T04:10:01Z",
    host_cpu_percent_p95: 42.5,
    host_rss_bytes_max: 536870912,
    db_pool_acquire_p95_ms: 1.2,
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

function assertRejected(result, pattern) {
  const text = `${JSON.stringify(result, null, 2)}\n`;
  assert.throws(
    () => validateEmploymentSeparationAcceptance(text, runtimeEvidence(text, result.selected_profile)),
    pattern,
  );
}

test("requires at least 1000 ordinary buyer-path iterations", () => {
  assertRejected(performanceResult("first_commit", 1), /at least 1000 iterations/);
});

test("requires at least 100 contention pairs", () => {
  assertRejected(performanceResult("contention", 99), /at least 100 iterations/);
});

test("requires fixed cardinality declarations in the result artifact", () => {
  const result = performanceResult("first_commit", 1000);
  result.minimum_non_contending_records = 1;
  result.minimum_contention_pairs = 1;
  assertRejected(result, /minimum_non_contending_records must equal 1000/);
});
