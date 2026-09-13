import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { validateEmploymentSeparationAcceptance } from "./employment_separation_acceptance_contract.mjs";
import {
  ACCEPTANCE_CANDIDATE_SHA,
  ACCEPTANCE_PROFILE_PRECONDITIONS,
  acceptanceFixtureSha256,
  acceptanceFixtureText,
} from "./employment_separation_acceptance_fixture_test_support.mjs";

function performanceResult(fixtureSha256, { includeFixtureDigest = true } = {}) {
  const value = {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
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
    profile_preconditions: { ...ACCEPTANCE_PROFILE_PRECONDITIONS },
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
  if (includeFixtureDigest) value.fixture_sha256 = fixtureSha256;
  return value;
}

function runtimeEvidence(resultText, fixtureSha256) {
  return {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    observed_service_sha: ACCEPTANCE_CANDIDATE_SHA,
    selected_profile: "first_commit",
    performance_result_sha256: createHash("sha256").update(resultText, "utf8").digest("hex"),
    fixture_sha256: fixtureSha256,
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

function render(value) {
  return `${JSON.stringify(value, null, 2)}\n`;
}

test("rejects acceptance without an exact fixture digest", () => {
  const fixtureText = acceptanceFixtureText();
  const fixtureSha256 = acceptanceFixtureSha256(fixtureText);
  const resultText = render(performanceResult(fixtureSha256, { includeFixtureDigest: false }));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultText, runtimeEvidence(resultText, fixtureSha256), fixtureText),
    /fixture_sha256/,
  );
});

test("rejects runtime evidence bound to a different fixture digest", () => {
  const fixtureText = acceptanceFixtureText();
  const fixtureSha256 = acceptanceFixtureSha256(fixtureText);
  const resultText = render(performanceResult(fixtureSha256));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultText, runtimeEvidence(resultText, "0".repeat(64)), fixtureText),
    /fixture_sha256/,
  );
});

test("rejects a fixture whose exact bytes are not right-cleared", () => {
  const fixtureText = acceptanceFixtureText({ rightCleared: false });
  const fixtureSha256 = acceptanceFixtureSha256(fixtureText);
  const resultText = render(performanceResult(fixtureSha256));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultText, runtimeEvidence(resultText, fixtureSha256), fixtureText),
    /right_cleared/,
  );
});

test("rejects a fixture whose exact bytes are synthetic", () => {
  const fixtureText = acceptanceFixtureText({ synthetic: true });
  const fixtureSha256 = acceptanceFixtureSha256(fixtureText);
  const resultText = render(performanceResult(fixtureSha256));
  assert.throws(
    () => validateEmploymentSeparationAcceptance(resultText, runtimeEvidence(resultText, fixtureSha256), fixtureText),
    /synthetic/,
  );
});

test("rejects byte-distinct fixture artifacts that collide after lossy UTF-8 decoding", () => {
  const fixtureBytes = Buffer.from(acceptanceFixtureText(), "utf8");
  const malformedA = Buffer.concat([Buffer.from([0x80]), fixtureBytes]);
  const malformedB = Buffer.concat([Buffer.from([0x81]), fixtureBytes]);
  assert.equal(malformedA.toString("utf8"), malformedB.toString("utf8"));
  assert.notEqual(
    createHash("sha256").update(malformedA).digest("hex"),
    createHash("sha256").update(malformedB).digest("hex"),
  );

  for (const malformed of [malformedA, malformedB]) {
    const fixtureSha256 = createHash("sha256").update(malformed).digest("hex");
    const resultText = render(performanceResult(fixtureSha256));
    assert.throws(
      () => validateEmploymentSeparationAcceptance(resultText, runtimeEvidence(resultText, fixtureSha256), malformed),
      /valid UTF-8/,
    );
  }
});
