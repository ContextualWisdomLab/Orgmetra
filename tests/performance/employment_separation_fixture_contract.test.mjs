import assert from "node:assert/strict";
import test from "node:test";

import {
  PERFORMANCE_FIXTURE_SCHEMA,
  requestBody,
  requestHeaders,
  validatePerformanceFixture,
} from "./employment_separation_fixture_contract.mjs";

const ZERO = "00000000-0000-0000-0000-000000000000";

function command(seed, key = `separation-key-${seed.toString().padStart(4, "0")}`) {
  const suffix = seed.toString(16).padStart(12, "0");
  return {
    tenant_record_id: `10000000-0000-4000-8000-${suffix}`,
    actor_reference: `worker_admin:perf_${seed}`,
    idempotency_key: key,
    payload: {
      person_record_id: `20000000-0000-4000-8000-${suffix}`,
      employment_record_id: `30000000-0000-4000-8000-${suffix}`,
      expected_employment_record_version_id: `40000000-0000-4000-8000-${suffix}`,
      separation_effective_on: "2026-09-13",
      separation_reason_code: "voluntary_resignation",
      evidence_reference: `evidence:perf_${seed}`,
      evidence_version_code: "v1",
      confirmation_reference: `confirmation:perf_${seed}`,
    },
  };
}

function fixture() {
  const left = command(4, "contention-key-left-0001");
  const right = structuredClone(left);
  right.idempotency_key = "contention-key-right-0001";
  return {
    schema_version: PERFORMANCE_FIXTURE_SCHEMA,
    candidate_sha: "a".repeat(40),
    right_cleared: true,
    synthetic: false,
    clearance_reference: "data-clearance:perf-2026-09",
    dataset_id: "dataset:employment-separation-perf-1",
    prepared_at: "2026-09-13T02:00:00Z",
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    profiles: {
      first_commit: [command(1)],
      replay: [command(2)],
      rejection: [command(3)],
      contention: [{ left, right }],
    },
  };
}

const smallAcceptance = { minimumNonContendingRecords: 1, minimumContentionPairs: 1 };

test("accepts a right-cleared fixture with isolated performance profiles", () => {
  const value = fixture();
  assert.equal(validatePerformanceFixture(value, smallAcceptance), value);
});

test("rejects synthetic or uncleared commercial fixtures", () => {
  const synthetic = fixture();
  synthetic.synthetic = true;
  assert.throws(() => validatePerformanceFixture(synthetic, smallAcceptance), /synthetic must be false/);

  const uncleared = fixture();
  uncleared.right_cleared = false;
  assert.throws(() => validatePerformanceFixture(uncleared, smallAcceptance), /right_cleared must be true/);
});

test("rejects sentinel identities and profile cross-contamination", () => {
  const sentinel = fixture();
  sentinel.profiles.first_commit[0].payload.person_record_id = ZERO;
  assert.throws(() => validatePerformanceFixture(sentinel, smallAcceptance), /operational UUID/);

  const overlap = fixture();
  overlap.profiles.replay[0].payload.employment_record_id = overlap.profiles.first_commit[0].payload.employment_record_id;
  assert.throws(() => validatePerformanceFixture(overlap, smallAcceptance), /reuses an Employment/);
});

test("requires contention commands to differ only by idempotency key", () => {
  const value = fixture();
  value.profiles.contention[0].right.payload.separation_reason_code = "retirement_transition";
  assert.throws(() => validatePerformanceFixture(value, smallAcceptance), /differ only by idempotency key/);
});

test("enforces minimum sample cardinality rather than silently shrinking the run", () => {
  assert.throws(
    () => validatePerformanceFixture(fixture(), { minimumNonContendingRecords: 2, minimumContentionPairs: 1 }),
    /at least 2 records/,
  );
});

test("matches the production Idempotency-Key length and visible-ASCII contract", () => {
  const shortKey = fixture();
  shortKey.profiles.first_commit[0].idempotency_key = "too-short";
  assert.throws(() => validatePerformanceFixture(shortKey, smallAcceptance), /16 to 200 visible ASCII/);

  const hiddenByte = fixture();
  hiddenByte.profiles.first_commit[0].idempotency_key = "valid-prefix-0001\n";
  assert.throws(() => validatePerformanceFixture(hiddenByte, smallAcceptance), /16 to 200 visible ASCII/);
});

test("builds the exact published separation request without storing bearer credentials in fixtures", () => {
  const value = command(9, "exact-key-00000001");
  const headers = requestHeaders(value, "opaque-token");
  assert.deepEqual(headers, {
    Authorization: "Bearer opaque-token",
    "Content-Type": "application/json",
    "Idempotency-Key": "exact-key-00000001",
    "X-Actor-Reference": "worker_admin:perf_9",
    "X-Purpose-Code": "workforce_admin",
    "X-Tenant-Reference": "10000000-0000-4000-8000-000000000009",
  });
  assert.deepEqual(JSON.parse(requestBody(value)), value.payload);
});
