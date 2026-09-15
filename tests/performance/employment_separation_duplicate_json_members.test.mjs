import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  acceptanceFixtureBytes,
  acceptanceFixtureSha256,
  acceptanceLoadModel,
} from "./employment_separation_acceptance_fixture_test_support.mjs";
import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

const CANDIDATE_SHA = "a".repeat(40);
const FIXTURE_BYTES = acceptanceFixtureBytes();

function performanceResult(fixtureSha256 = acceptanceFixtureSha256(FIXTURE_BYTES)) {
  return {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: CANDIDATE_SHA,
    fixture_sha256: fixtureSha256,
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

function render(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function runtimeEvidence(resultArtifact, fixtureSha256 = acceptanceFixtureSha256(FIXTURE_BYTES)) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: CANDIDATE_SHA,
    observed_service_sha: CANDIDATE_SHA,
    selected_profile: "first_commit",
    performance_result_sha256: createHash("sha256").update(resultArtifact).digest("hex"),
    fixture_sha256: fixtureSha256,
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

function duplicateCandidateSha(bytes) {
  const text = bytes.toString("utf8");
  const needle = `"candidate_sha": "${CANDIDATE_SHA}"`;
  const replacement = `"candidate_sha": "${"b".repeat(40)}",\n  "candidate_\\u0073ha": "${CANDIDATE_SHA}"`;
  assert.notEqual(text.indexOf(needle), -1);
  return Buffer.from(text.replace(needle, replacement), "utf8");
}

test("rejects escaped-equivalent duplicate member names in result bytes", () => {
  const resultArtifact = duplicateCandidateSha(render(performanceResult()));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact),
      FIXTURE_BYTES,
    ),
    /duplicate JSON object member name/,
  );
});

test("rejects escaped-equivalent duplicate member names in fixture bytes", () => {
  const fixtureArtifact = duplicateCandidateSha(FIXTURE_BYTES);
  const fixtureSha256 = acceptanceFixtureSha256(fixtureArtifact);
  const resultArtifact = render(performanceResult(fixtureSha256));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact, fixtureSha256),
      fixtureArtifact,
    ),
    /duplicate JSON object member name/,
  );
});

test("rejects duplicate runtime evidence member names before JSON last-value-wins collapse", () => {
  const runtimeArtifact = Buffer.from(
    `{"candidate_sha":"${"b".repeat(40)}","candidate_\\u0073ha":"${CANDIDATE_SHA}"}`,
    "utf8",
  );
  assert.throws(() => parseRuntimeEvidenceArtifact(runtimeArtifact), /duplicate JSON object member name/);
});

test("rejects duplicate member names recursively in nested result objects", () => {
  const text = render(performanceResult()).toString("utf8");
  const needle = '"checks": {';
  const resultArtifact = Buffer.from(text.replace(needle, '"checks": {"values":{"rate":0}}, "ch\\u0065cks": {'), "utf8");
  assert.throws(
    () => validateEmploymentSeparationAcceptance(
      resultArtifact,
      runtimeEvidence(resultArtifact),
      FIXTURE_BYTES,
    ),
    /duplicate JSON object member name/,
  );
});
