import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

const candidateSha = "a".repeat(40);
const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);

function performanceResult(latencySamples = 1000, trendSamples = latencySamples) {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: candidateSha,
    fixture_sha256: FIXTURE_SHA256,
    selected_profile: "first_commit",
    expected_iterations: 1000,
    completed_iterations: 1000,
    sample_complete: true,
    completed_at: "2026-09-13T04:10:00Z",
    load_model: acceptanceLoadModel(1000),
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
        iterations: { values: { count: 1000 } },
        dropped_iterations: { values: { count: 0 } },
        checks: { values: { rate: 1 } },
        employment_separation_unexpected_response: { values: { rate: 0 } },
        employment_separation_latency_samples: { values: { count: latencySamples } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8, "p(95)": 18, "p(99)": 19, max: 22, count: trendSamples },
        },
      },
    },
  };
}

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function runtimeEvidence(resultArtifact) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: candidateSha,
    observed_service_sha: candidateSha,
    selected_profile: "first_commit",
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

test("rejects a complete iteration count with an incomplete latency counter", () => {
  const artifact = render(performanceResult(999, 1000));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(artifact, runtimeEvidence(artifact), FIXTURE_BYTES),
    /latency sample count/,
  );
});

test("rejects a complete counter when the measured Trend itself is truncated", () => {
  const artifact = render(performanceResult(1000, 999));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(artifact, runtimeEvidence(artifact), FIXTURE_BYTES),
    /Trend sample count/,
  );
});

test("accepts latency evidence only when every expected request contributed to the measured Trend", () => {
  const artifact = render(performanceResult(1000, 1000));
  const accepted = validateEmploymentSeparationAcceptance(artifact, runtimeEvidence(artifact), FIXTURE_BYTES);
  assert.equal(accepted.accepted, true);
  assert.equal(accepted.p95_ms, 18);
});
