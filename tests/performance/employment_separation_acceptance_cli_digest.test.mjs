import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const acceptanceCheck = fileURLToPath(new URL("./employment_separation_acceptance_check.mjs", import.meta.url));

const PERFORMANCE_ATTESTATION_GAP_PATTERN = /authenticated performance-evidence attestation.*ContextualWisdomLab\/.github#2162/;
const DEPLOYMENT_IDENTITY_GAP_PATTERN = /authenticated deployed-candidate evidence.*ContextualWisdomLab\/Orgmetra#395/;

function assertCommercialOwnerGaps(stderr) {
  assert.match(stderr, PERFORMANCE_ATTESTATION_GAP_PATTERN);
  assert.match(stderr, DEPLOYMENT_IDENTITY_GAP_PATTERN);
}

test("commercial acceptance fails closed before trusting a caller-supplied result digest", () => {
  const result = spawnSync(
    process.execPath,
    [acceptanceCheck, "result.json", "runtime.json", "fixture.json", "a".repeat(64)],
    { encoding: "utf8" },
  );
  assert.notEqual(result.status, 0);
  assertCommercialOwnerGaps(result.stderr);
});

test("commercial acceptance cannot be restored by substituting both result bytes and digest locally", () => {
  const result = spawnSync(
    process.execPath,
    [acceptanceCheck, "substituted-result.json", "substituted-runtime.json", "fixture.json", "b".repeat(64)],
    { encoding: "utf8" },
  );
  assert.notEqual(result.status, 0);
  assertCommercialOwnerGaps(result.stderr);
});
