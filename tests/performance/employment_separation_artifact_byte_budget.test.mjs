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
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

const MAXIMUM_RESULT_ARTIFACT_BYTES = 1024 * 1024;
const MAXIMUM_RUNTIME_EVIDENCE_BYTES = 1024 * 1024;
const MAXIMUM_FIXTURE_ARTIFACT_BYTES = 8 * 1024 * 1024;
const ITERATIONS = 1000;

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function padWithJsonWhitespace(bytes, maximumBytes) {
  assert.ok(bytes.length <= maximumBytes, "test fixture must fit within the declared byte budget");
  return Buffer.concat([
    bytes,
    Buffer.alloc(maximumBytes + 1 - bytes.length, 0x20),
  ]);
}

function result(fixtureSha256) {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    fixture_sha256: fixtureSha256,
    selected_profile: "first_commit",
    expected_iterations: ITERATIONS,
    completed_iterations: ITERATIONS,
    sample_complete: true,
    completed_at: "2026-09-13T04:10:00Z",
    load_model: acceptanceLoadModel(ITERATIONS),
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
        iterations: { values: { count: ITERATIONS } },
        checks: { values: { rate: 1, passes: ITERATIONS, fails: 0 } },
        employment_separation_unexpected_response: { values: { rate: 0, passes: 0, fails: ITERATIONS } },
        employment_separation_latency_samples: { values: { count: ITERATIONS } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8, "p(95)": 18, "p(99)": 19, max: 22, count: ITERATIONS },
        },
      },
    },
  };
}

function runtime(resultArtifact, fixtureSha256) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    observed_service_sha: ACCEPTANCE_CANDIDATE_SHA,
    selected_profile: "first_commit",
    performance_result_sha256: createHash("sha256").update(resultArtifact).digest("hex"),
    fixture_sha256: fixtureSha256,
    environment_reference: "environment:perf-staging-1",
    deployment_reference: "deployment:orgmetra-people-a1",
    observer_reference: "observer:perf-runtime-1",
    load_observation_reference: "evidence:perf-load-observation-1",
    observed_load_model: acceptanceLoadModel(ITERATIONS),
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

test("rejects oversized runtime evidence before UTF-8 decode or JSON scanning", () => {
  const oversized = padWithJsonWhitespace(Buffer.from("{}", "utf8"), MAXIMUM_RUNTIME_EVIDENCE_BYTES);
  assert.throws(
    () => parseRuntimeEvidenceArtifact(oversized),
    /runtime evidence must not exceed 1048576 bytes/,
  );
});

test("rejects oversized performance-result evidence before UTF-8 decode or JSON scanning", () => {
  const fixtureBytes = acceptanceFixtureBytes();
  const fixtureSha256 = acceptanceFixtureSha256(fixtureBytes);
  const resultBytes = padWithJsonWhitespace(render(result(fixtureSha256)), MAXIMUM_RESULT_ARTIFACT_BYTES);

  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultBytes,
      runtime(resultBytes, fixtureSha256),
      fixtureBytes,
    ),
    /performance result must not exceed 1048576 bytes/,
  );
});

test("rejects oversized performance-fixture evidence before UTF-8 decode or JSON scanning", () => {
  const fixtureBytes = padWithJsonWhitespace(acceptanceFixtureBytes(), MAXIMUM_FIXTURE_ARTIFACT_BYTES);
  const fixtureSha256 = acceptanceFixtureSha256(fixtureBytes);
  const resultBytes = render(result(fixtureSha256));

  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultBytes,
      runtime(resultBytes, fixtureSha256),
      fixtureBytes,
    ),
    /performance fixture must not exceed 8388608 bytes/,
  );
});
