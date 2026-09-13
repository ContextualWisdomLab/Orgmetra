import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";

function result() {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: "a".repeat(40),
    selected_profile: "first_commit",
    expected_iterations: 1000,
    completed_iterations: 1000,
    sample_complete: true,
    completed_at: "2026-09-13T04:10:00Z",
    dataset_id: "dataset:employment-separation-perf-1",
    clearance_reference: "data_clearance:perf-2026-09",
    preparation_protocol_reference: "protocol:employment-separation-perf-v1",
    prepared_state_evidence_reference: "evidence:prepared-state-perf-1",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    profile_preconditions: {
      first_commit: "active_current_expected_version",
      replay: "same_key_same_semantics_already_committed",
      rejection: "expected_version_stale_or_semantic_conflict",
      contention: "active_current_expected_version",
    },
    minimum_non_contending_records: 1000,
    minimum_contention_pairs: 100,
    k6: {
      metrics: {
        iterations: { values: { count: 1000, rate: 40 } },
        checks: { values: { rate: 1, passes: 1000, fails: 0 } },
        employment_separation_unexpected_response: { values: { rate: 0, passes: 0, fails: 1000 } },
        employment_separation_latency_samples: { values: { count: 1000, rate: 40 } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3 },
        },
      },
    },
  };
}

function runtimeEvidence(resultText) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: "a".repeat(40),
    observed_service_sha: "a".repeat(40),
    selected_profile: "first_commit",
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

function evidencePair() {
  const performance = result();
  const text = `${JSON.stringify(performance, null, 2)}\n`;
  return { performance, text, runtime: runtimeEvidence(text) };
}

test("accepts an exact candidate result only with bound deployment, resource, and cleanup evidence", () => {
  const { text, runtime } = evidencePair();
  assert.deepEqual(validateEmploymentSeparationAcceptance(text, runtime), {
    accepted: true,
    candidate_sha: "a".repeat(40),
    selected_profile: "first_commit",
    performance_result_sha256: runtime.performance_result_sha256,
    p95_ms: 18.4,
  });
});

test("rejects a self-declared target when the observed service revision differs", () => {
  const { text, runtime } = evidencePair();
  runtime.observed_service_sha = "b".repeat(40);
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtime), /observed_service_sha must match candidate_sha/);
});

test("rejects a result artifact that is not the one observed by the runtime evidence", () => {
  const { text, runtime } = evidencePair();
  runtime.performance_result_sha256 = "0".repeat(64);
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtime), /performance_result_sha256/);
});

test("rejects first-commit evidence above the commercial p95 target", () => {
  const { performance } = evidencePair();
  performance.k6.metrics.employment_separation_first_commit_duration_ms.values["p(95)"] = 20.001;
  performance.k6.metrics.employment_separation_first_commit_duration_ms.values["p(99)"] = 21;
  const text = `${JSON.stringify(performance, null, 2)}\n`;
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtimeEvidence(text)), /p95 must be <= 20 ms/);
});

test("rejects incomplete samples even when the completed subset is fast", () => {
  const { performance } = evidencePair();
  performance.completed_iterations = 999;
  performance.sample_complete = false;
  performance.k6.metrics.iterations.values.count = 999;
  performance.k6.metrics.employment_separation_latency_samples.values.count = 999;
  const text = `${JSON.stringify(performance, null, 2)}\n`;
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtimeEvidence(text)), /sample must be complete/);
});

test("rejects acceptance when post-run cleanup finds a run-scoped leak", () => {
  const { text, runtime } = evidencePair();
  runtime.residual_open_transactions = 1;
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtime), /residual_open_transactions must be 0/);
});

test("rejects missing CPU, memory, or pool observations instead of accepting latency alone", () => {
  const { text, runtime } = evidencePair();
  runtime.db_pool_acquire_p95_ms = null;
  assert.throws(() => validateEmploymentSeparationAcceptance(text, runtime), /db_pool_acquire_p95_ms/);
});
