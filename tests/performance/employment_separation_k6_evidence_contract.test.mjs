import assert from "node:assert/strict";
import test from "node:test";

import {
  PINNED_K6_IMAGE,
  PINNED_K6_IMAGE_DIGEST,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
} from "./employment_separation_k6_runtime_contract.mjs";
import { validatePinnedK6AcceptanceEvidence } from "./employment_separation_k6_evidence_contract.mjs";

function resultBytes(overrides = {}) {
  return Buffer.from(`${JSON.stringify({
    k6_version: PINNED_K6_VERSION,
    k6_image: PINNED_K6_IMAGE,
    k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    ...overrides,
  })}\n`, "utf8");
}
function runtime(overrides = {}) {
  return {
    observed_k6_version: PINNED_K6_VERSION,
    observed_k6_image: PINNED_K6_IMAGE,
    observed_k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    observed_k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
    ...overrides,
  };
}

test("binds result identity to independently observed pinned upstream k6 OCI evidence", () => {
  assert.deepEqual(validatePinnedK6AcceptanceEvidence(resultBytes(), runtime()), {
    k6_version: PINNED_K6_VERSION,
    k6_image: PINNED_K6_IMAGE,
    k6_image_digest: PINNED_K6_IMAGE_DIGEST,
    k6_runner_identity: PINNED_K6_RUNNER_IDENTITY,
  });
});

test("rejects matching-but-unpinned image digests in result evidence", () => {
  const fake = `sha256:${"0".repeat(64)}`;
  assert.throws(() => validatePinnedK6AcceptanceEvidence(resultBytes({ k6_image_digest: fake }), runtime({ observed_k6_image_digest: fake })), /OCI image digest/);
});

test("rejects runtime observation that does not identify the exact pinned image", () => {
  assert.throws(() => validatePinnedK6AcceptanceEvidence(resultBytes(), runtime({ observed_k6_runner_identity: "ghcr.io/grafana/k6@sha256:substitute" })), /runner identity/);
});

test("rejects oversized result evidence before UTF-8 decode or JSON scanning", () => {
  const ordinary = resultBytes();
  const oversized = Buffer.concat([
    ordinary,
    Buffer.alloc((1024 * 1024) + 1 - ordinary.length, 0x20),
  ]);
  assert.throws(
    () => validatePinnedK6AcceptanceEvidence(oversized, runtime()),
    /performance result must not exceed 1048576 bytes/,
  );
});

test("rejects escaped-equivalent duplicate k6 identity members before JSON collapse", () => {
  const duplicate = Buffer.from(
    `{\"k6_version\":${JSON.stringify(PINNED_K6_VERSION)},`
      + `\"k6_image\":${JSON.stringify(PINNED_K6_IMAGE)},`
      + `\"k6_image_digest\":\"sha256:${"0".repeat(64)}\",`
      + `\"k6_image_\\u0064igest\":${JSON.stringify(PINNED_K6_IMAGE_DIGEST)},`
      + `\"k6_runner_identity\":${JSON.stringify(PINNED_K6_RUNNER_IDENTITY)}}\n`,
    "utf8",
  );

  assert.doesNotThrow(() => JSON.parse(duplicate.toString("utf8")));
  assert.throws(
    () => validatePinnedK6AcceptanceEvidence(duplicate, runtime()),
    /duplicate JSON object member name "k6_image_digest"/,
  );
});
