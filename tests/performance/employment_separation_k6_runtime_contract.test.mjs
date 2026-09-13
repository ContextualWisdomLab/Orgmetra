import assert from "node:assert/strict";
import test from "node:test";

import {
  PINNED_K6_RELEASE_ASSET,
  PINNED_K6_RELEASE_ASSET_SHA256,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
  requirePinnedK6Runtime,
  requirePinnedK6Version,
} from "./employment_separation_k6_runtime_contract.mjs";

const EXECUTABLE_SHA256 = "1".repeat(64);

function validRuntime() {
  return {
    version: PINNED_K6_VERSION,
    releaseAsset: PINNED_K6_RELEASE_ASSET,
    releaseAssetSha256: PINNED_K6_RELEASE_ASSET_SHA256,
    runnerIdentity: PINNED_K6_RUNNER_IDENTITY,
    executableSha256: EXECUTABLE_SHA256,
  };
}

test("accepts only the repository-pinned upstream k6 release artifact", () => {
  assert.equal(PINNED_K6_VERSION, "2.2.0");
  assert.equal(requirePinnedK6Version("2.2.0"), "2.2.0");
  assert.deepEqual(requirePinnedK6Runtime(validRuntime()), {
    version: PINNED_K6_VERSION,
    release_asset: PINNED_K6_RELEASE_ASSET,
    release_asset_sha256: PINNED_K6_RELEASE_ASSET_SHA256,
    runner_identity: PINNED_K6_RUNNER_IDENTITY,
    executable_sha256: EXECUTABLE_SHA256,
  });
});

test("rejects substituted versions, archives, digests, identities, and malformed executable hashes", () => {
  for (const value of ["", "2.1.0", "2.2.1", "2.3.0", "v2.2.0", "2.2.0-dev"]) {
    assert.throws(() => requirePinnedK6Version(value), /require k6 2\.2\.0/);
  }
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), releaseAsset: "k6-substitute.tar.gz" }), /require k6-v2\.2\.0-linux-amd64\.tar\.gz/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), releaseAssetSha256: "0".repeat(64) }), /release-asset SHA-256/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), runnerIdentity: "upstream_release_archive:substitute" }), /runner identity/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), executableSha256: "not-a-sha" }), /executable SHA-256/);
});
