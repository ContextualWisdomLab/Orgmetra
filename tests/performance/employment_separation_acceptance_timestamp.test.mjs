import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  ACCEPTANCE_CANDIDATE_SHA,
  ACCEPTANCE_PROFILE_PRECONDITIONS,
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function performanceResult() {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
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
    profile_preconditions: { ...ACCEPTANCE_PROFILE_PRECONDITIONS },
    minimum_non_contending_records: 1000,
    minimum_contention_pairs: 100,
    k6: {
      metrics: {
        iterations: { values: { count: 1000, rate: 20 } },
        checks: { values: { rate: 1, passes: 1000, fails: 0 } },
        employment_separation_unexpected_response: { values: { rate: 0, passes: 0, fails: 1000 } },
        employment_separation_latency_samples: { values: { count: 1000, rate: 20 } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3, count: 1000 },
        },
      },
    },
  };
}

function runtimeEvidence(resultArtifact) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    observed_service_sha: ACCEPTANCE_CANDIDATE_SHA,
    selected_profile: "first_commit",
    performance_result_sha256: createHash("sha256").update(resultArtifact).digest("hex"),
    fixture_sha256: FIXTURE_SHA256,
    environment_reference: "environment:perf-staging-1",
    deployment_reference: "deployment:orgmetra-people-a1",
    observer_reference: "observer:perf-runtime-1",
    load_observation_reference: "evidence:perf-load-observation-1",
    observed_load_model: acceptanceLoadModel(1000),
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

test("rejects an impossible result completion calendar date instead of accepting Date.parse normalization", () => {
  const performance = performanceResult();
  performance.completed_at = "2026-02-30T04:10:00Z";
  const artifact = render(performance);

  assert.throws(
    () => validateEmploymentSeparationAcceptance(artifact, runtimeEvidence(artifact), FIXTURE_BYTES),
    /result.completed_at must be an RFC 3339 UTC timestamp/,
  );
});

test("rejects an impossible runtime observation calendar date instead of accepting Date.parse normalization", () => {
  const performance = performanceResult();
  const artifact = render(performance);
  const runtime = runtimeEvidence(artifact);
  runtime.observed_at = "2026-09-31T04:10:01Z";

  assert.throws(
    () => validateEmploymentSeparationAcceptance(artifact, runtime, FIXTURE_BYTES),
    /runtime.observed_at must be an RFC 3339 UTC timestamp/,
  );
});

test("rejects a sub-millisecond runtime observation that precedes completion", () => {
  const performance = performanceResult();
  performance.completed_at = "2026-09-13T04:10:00.0009Z";
  const artifact = render(performance);
  const runtime = runtimeEvidence(artifact);
  runtime.observed_at = "2026-09-13T04:10:00.0001Z";

  assert.throws(
    () => validateEmploymentSeparationAcceptance(artifact, runtime, FIXTURE_BYTES),
    /runtime.observed_at must not precede result.completed_at/,
  );
});

test("accepts equivalent fractional instants with trailing-zero spelling differences", () => {
  const performance = performanceResult();
  performance.completed_at = "2026-09-13T04:10:00.100Z";
  const artifact = render(performance);
  const runtime = runtimeEvidence(artifact);
  runtime.observed_at = "2026-09-13T04:10:00.1000Z";

  const evidence = validateEmploymentSeparationAcceptance(artifact, runtime, FIXTURE_BYTES);
  assert.equal(evidence.structurally_valid, true);
});
