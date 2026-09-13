import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import {
  validateEmploymentSeparationAcceptance,
  validateRunnerResultDigest,
} from "./employment_separation_acceptance_contract.mjs";
import {
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

const PROFILE_PRECONDITIONS = Object.freeze({
  first_commit: "active_current_expected_version",
  replay: "same_key_same_semantics_already_committed",
  rejection: "expected_version_stale_or_semantic_conflict",
  contention: "active_current_expected_version",
});
const FIXTURE_BYTES = acceptanceFixtureBytes();
const FIXTURE_SHA256 = acceptanceFixtureSha256(FIXTURE_BYTES);

function result() {
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
    profile_preconditions: { ...PROFILE_PRECONDITIONS },
    minimum_non_contending_records: 1000,
    minimum_contention_pairs: 100,
    k6: {
      metrics: {
        iterations: { values: { count: 1000 } },
        checks: { values: { rate: 1 } },
        employment_separation_unexpected_response: { values: { rate: 0 } },
        employment_separation_latency_samples: { values: { count: 1000 } },
        employment_separation_first_commit_duration_ms: {
          values: { "p(50)": 8, "p(95)": 18, "p(99)": 19, max: 22, count: 1000 },
        },
      },
    },
  };
}

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function runtime(resultArtifact) {
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

function reject(mutate, pattern) {
  const value = result();
  mutate(value);
  const artifact = render(value);
  assert.throws(() => validateEmploymentSeparationAcceptance(artifact, runtime(artifact), FIXTURE_BYTES), pattern);
}

test("requires right-cleared dataset and preparation provenance references", () => {
  for (const field of [
    "dataset_id",
    "clearance_reference",
    "preparation_protocol_reference",
    "prepared_state_evidence_reference",
  ]) {
    reject((value) => { delete value[field]; }, new RegExp(`result\\.${field}`));
    reject((value) => { value[field] = "not namespaced"; }, new RegExp(`result\\.${field}`));
  }
});

test("requires exact profile-precondition vocabulary", () => {
  reject((value) => { delete value.profile_preconditions; }, /result\.profile_preconditions/);
  reject((value) => { value.profile_preconditions = []; }, /result\.profile_preconditions/);
  reject((value) => { delete value.profile_preconditions.replay; }, /exactly first_commit, replay, rejection, contention/);
  reject((value) => { value.profile_preconditions.replay = "already_committed_maybe"; }, /profile_preconditions\.replay/);
  reject((value) => { value.profile_preconditions.extra = "unexpected"; }, /exactly first_commit, replay, rejection, contention/);
});

test("requires exact open-load and direct-network provenance", () => {
  reject((value) => { delete value.load_model; }, /load_model must be an object/);
  reject((value) => { value.load_model.executor = "shared-iterations"; }, /constant-arrival-rate/);
  reject((value) => { value.load_model.client_network_topology = "https_mitm_proxy"; }, /client_network_topology/);
});

test("binds later acceptance to the exact digest emitted by the benchmark runner", () => {
  const artifact = render(result());
  const digest = createHash("sha256").update(artifact).digest("hex");
  assert.equal(validateRunnerResultDigest(artifact, digest), digest);

  const substituted = Buffer.concat([artifact, Buffer.from(" ", "utf8")]);
  assert.throws(
    () => validateRunnerResultDigest(substituted, digest),
    /runner result digest does not bind the supplied performance result/,
  );
});

test("rejects malformed runner result digests before acceptance", () => {
  const artifact = render(result());
  assert.throws(
    () => validateRunnerResultDigest(artifact, "not-a-sha256"),
    /runner result digest must be a SHA-256 digest/,
  );
});
