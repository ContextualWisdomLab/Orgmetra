import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  PINNED_K6_IMAGE,
  PINNED_K6_IMAGE_DIGEST,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
  requirePinnedK6Runtime,
  requirePinnedK6Version,
} from "./employment_separation_k6_runtime_contract.mjs";

function validRuntime() {
  return {
    version: PINNED_K6_VERSION,
    image: PINNED_K6_IMAGE,
    imageDigest: PINNED_K6_IMAGE_DIGEST,
    runnerIdentity: PINNED_K6_RUNNER_IDENTITY,
  };
}

test("accepts only the repository-pinned upstream k6 OCI image", () => {
  assert.equal(PINNED_K6_VERSION, "2.2.0");
  assert.equal(requirePinnedK6Version("2.2.0"), "2.2.0");
  assert.deepEqual(requirePinnedK6Runtime(validRuntime()), {
    version: PINNED_K6_VERSION,
    image: PINNED_K6_IMAGE,
    image_digest: PINNED_K6_IMAGE_DIGEST,
    runner_identity: PINNED_K6_RUNNER_IDENTITY,
  });
});

test("rejects substituted versions, images, digests, and runner identities", () => {
  for (const value of ["", "2.1.0", "2.2.1", "2.3.0", "v2.2.0", "2.2.0-dev"]) {
    assert.throws(() => requirePinnedK6Version(value), /require k6 2\.2\.0/);
  }
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), image: "example.invalid/k6" }), /require ghcr\.io\/grafana\/k6/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), imageDigest: `sha256:${"0".repeat(64)}` }), /OCI image digest/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), runnerIdentity: "ghcr.io/grafana/k6@sha256:substitute" }), /runner identity/);
});

test("canonical benchmark runner does not accept ungoverned k6 CLI overrides", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.doesNotMatch(
    runner,
    /"\$@"/,
    "arbitrary k6 CLI flags can override version-controlled script options and __ENV inputs",
  );
  assert.match(
    runner,
    /"\$\{PINNED_K6_RUNNER_IDENTITY\}" run "\$\{WORKLOAD\}"\s*$/m,
    "commercial measurement must end at the version-controlled workload without caller-supplied k6 flags",
  );
});

test("canonical benchmark runner rejects CLI overrides before any Podman dependency is needed", () => {
  const runnerPath = fileURLToPath(new URL("./run_employment_separation_benchmark.sh", import.meta.url));
  const result = spawnSync("bash", [runnerPath, "--duration", "1s"], {
    encoding: "utf8",
    env: { PATH: process.env.PATH ?? "" },
  });
  assert.equal(result.status, 64);
  assert.match(result.stderr, /does not accept caller-supplied k6 CLI options/);
});
