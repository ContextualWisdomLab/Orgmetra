import assert from "node:assert/strict";
import test from "node:test";

import {
  PINNED_K6_RELEASE_ASSET,
  PINNED_K6_RELEASE_ASSET_SHA256,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
} from "./employment_separation_k6_runtime_contract.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";

const EXECUTABLE_SHA256 = "1".repeat(64);

function resultBytes(overrides = {}) {
  return Buffer.from(`${JSON.stringify({
    k6_version: PINNED_K6_VERSION,
    k6_release_asset: PINNED_K6_RELEASE_ASSET,
    k6_release_asset_sha256: PINNED_K6_RELEASE_ASSET_SHA256,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    k6_executable_sha256: EXECUTABLE_SHA256,
    ...overrides,
  })}\n`, "utf8");
}

function runtime(overrides = {}) {
  return {
    observed_k6_version: PINNED_K6_VERSION,
    observed_k6_release_asset: PINNED_K6_RELEASE_ASSET,
    observed_k6_release_asset_sha256: PINNED_K6_RELEASE_ASSET_SHA256,
    observed_k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    observed_k6_executable_sha256: EXECUTABLE_SHA256,
    ...overrides,
  };
}

test("binds result runtime identity to independently observed pinned upstream k6 evidence", () => {
  assert.deepEqual(validatePinnedK6AcceptanceEvidence(resultBytes(), runtime()), {
    k6_version: PINNED_K6_VERSION,
    k6_release_asset: PINNED_K6_RELEASE_ASSET,
    k6_release_asset_sha256: PINNED_K6_RELEASE_ASSET_SHA256,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    k6_executable_sha256: EXECUTABLE_SHA256,
  });
});

test("rejects a result that merely self-declares the right version with a substituted archive", () => {
  assert.throws(
    () => validatePinnedK6AcceptanceEvidence(resultBytes({ k6_release_asset_sha256: "0".repeat(64) }), runtime()),
    /release-asset SHA-256/,
  );
});

test("rejects runtime observation that does not identify the exact pinned runner", () => {
  assert.throws(
    () => validatePinnedK6AcceptanceEvidence(resultBytes(), runtime({ observed_k6_runner_identity: "upstream_release_archive:substitute" })),
    /runner identity/,
  );
});

test("rejects an independently observed executable digest that differs from the result", () => {
  assert.throws(
    () => validatePinnedK6AcceptanceEvidence(resultBytes(), runtime({ observed_k6_executable_sha256: "2".repeat(64) })),
    /executable_sha256 must match/,
  );
});
