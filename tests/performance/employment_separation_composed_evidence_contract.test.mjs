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
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";
import {
  PINNED_K6_IMAGE,
  PINNED_K6_IMAGE_DIGEST,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
} from "./employment_separation_k6_runtime_contract.mjs";

const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);
const ITERATIONS = 1000;

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function performanceResult() {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    fixture_sha256: FIXTURE_SHA256,
    k6_version: PINNED_K6_VERSION,
    k6_image: PINNED_K6_IMAGE,
    k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
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
        checks: { values: { rate: 1 } },
        employment_separation_unexpected_response: { values: { rate: 0 } },
        employment_separation_latency_samples: { values: { count: ITERATIONS } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8, "p(95)": 18, "p(99)": 19, max: 22, count: ITERATIONS },
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
    observed_k6_version: PINNED_K6_VERSION,
    observed_k6_image: PINNED_K6_IMAGE,
    observed_k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    observed_k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    selected_profile: "first_commit",
    performance_result_sha256: createHash("sha256").update(resultArtifact).digest("hex"),
    fixture_sha256: FIXTURE_SHA256,
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

test("one evidence pair satisfies both structural and pinned-k6 contracts", () => {
  const resultArtifact = render(performanceResult());
  const runtime = runtimeEvidence(resultArtifact);

  const structural = validateEmploymentSeparationAcceptance(resultArtifact, runtime, FIXTURE_BYTES);
  const pinned = validatePinnedK6AcceptanceEvidence(resultArtifact, runtime);

  assert.equal(structural.structurally_valid, true);
  assert.deepEqual(pinned, {
    k6_version: PINNED_K6_VERSION,
    k6_image: PINNED_K6_IMAGE,
    k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
  });
});

test("structural schema rejects a partial result k6 identity group", () => {
  const result = performanceResult();
  delete result.k6_runner_identity;
  const resultArtifact = render(result);

  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact),
      FIXTURE_BYTES,
    ),
    /either all or none of k6_version, k6_image, k6_image_digest, k6_runner_identity/,
  );
});

test("structural schema rejects a partial runtime k6 identity group", () => {
  const resultArtifact = render(performanceResult());
  const runtime = runtimeEvidence(resultArtifact);
  delete runtime.observed_k6_runner_identity;

  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultArtifact, runtime, FIXTURE_BYTES),
    /either all or none of observed_k6_version, observed_k6_image, observed_k6_image_digest, observed_k6_runner_identity/,
  );
});

test("structural schema rejects non-string declared k6 identity evidence", () => {
  const result = performanceResult();
  result.k6_version = 220;
  const resultArtifact = render(result);

  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact),
      FIXTURE_BYTES,
    ),
    /result.k6_version must be a non-empty string/,
  );
});
