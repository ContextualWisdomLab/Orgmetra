import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);

function performanceResult() {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: "a".repeat(40),
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
        iterations: { values: { count: 1000, rate: 40 } },
        checks: { values: { rate: 1, passes: 1000, fails: 0 } },
        employment_separation_unexpected_response: { values: { rate: 0, passes: 0, fails: 1000 } },
        employment_separation_latency_samples: { values: { count: 1000, rate: 40 } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8.1, "p(95)": 18.4, "p(99)": 19.7, max: 22.3, count: 1000 },
        },
      },
    },
  };
}

function artifact(result) {
  return Buffer.from(`${JSON.stringify(result, null, 2)}\n`, "utf8");
}

function runtimeEvidence(resultArtifact) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: "a".repeat(40),
    observed_service_sha: "a".repeat(40),
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

test("rejects undeclared top-level result evidence fields", () => {
  const result = performanceResult();
  result.unreviewed_extension = "must-not-be-ignored";
  const resultArtifact = artifact(result);

  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact),
      FIXTURE_BYTES,
    ),
    /result must contain exactly/,
  );
});

test("rejects undeclared top-level runtime evidence fields", () => {
  const resultArtifact = artifact(performanceResult());
  const runtime = runtimeEvidence(resultArtifact);
  runtime.unreviewed_extension = "must-not-be-ignored";

  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultArtifact, runtime, FIXTURE_BYTES),
    /runtime must contain exactly/,
  );
});
