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

test("canonical benchmark runner does not forward caller-controlled load-model environment", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  for (const name of [
    "ORGMETRA_PERFORMANCE_TARGET_RPS",
    "ORGMETRA_PERFORMANCE_DURATION_SECONDS",
    "ORGMETRA_PERFORMANCE_PREALLOCATED_VUS",
    "ORGMETRA_PERFORMANCE_MAX_VUS",
  ]) {
    assert.doesNotMatch(runner, new RegExp(`--env ${name}(?:\\s|$)`), `${name} must be version-controlled by the workload`);
  }
});

test("canonical benchmark runner binds the mounted workload to an immutable exact-candidate image", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" rev-parse --verify HEAD/,
    "the source repository must be checked against an exact HEAD before materialization",
  );
  assert.match(
    runner,
    /repository_head.*ORGMETRA_PERFORMANCE_TARGET_SHA|ORGMETRA_PERFORMANCE_TARGET_SHA.*repository_head/s,
    "the exact source checkout must match the measured candidate SHA",
  );
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" status --porcelain=v1 --untracked-files=all/,
    "commercial evidence must reject modified, staged, or untracked source bytes",
  );
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" archive --format=tar "\$\{target_sha\}"[\s\S]*podman import/,
    "the executed workload must be imported from the verified immutable candidate commit",
  );
  assert.doesNotMatch(
    runner,
    /--volume "\$\{repo_root\}:\/workspace:ro"/,
    "the live host working tree must never be mounted as the executable workload",
  );
  assert.match(
    runner,
    /--mount "type=image,source=\$\{workload_image_id\},destination=\/workspace"/,
    "Podman must mount only the imported candidate image at /workspace",
  );
  assert.match(
    runner,
    /podman image rm --force "\$\{workload_image_id\}"/,
    "the ephemeral candidate image must be removed after the run",
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
