import assert from "node:assert/strict";
import { mkdtempSync, rmSync, truncateSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";

const runner = fileURLToPath(new URL("./run_employment_separation_benchmark.sh", import.meta.url));
const MAXIMUM_FIXTURE_ARTIFACT_BYTES = 8 * 1024 * 1024;

function repositoryHead() {
  const result = spawnSync("git", ["rev-parse", "--verify", "HEAD"], {
    cwd: fileURLToPath(new URL("../..", import.meta.url)),
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

test("runner rejects an oversized fixture before Podman availability or image checks", () => {
  const directory = mkdtempSync(join(tmpdir(), "orgmetra-perf-fixture-budget-"));
  try {
    const fixture = join(directory, "fixture.json");
    const summary = join(directory, "summary.json");
    truncateSync(fixture, MAXIMUM_FIXTURE_ARTIFACT_BYTES + 1);

    const result = spawnSync("bash", [runner], {
      cwd: fileURLToPath(new URL("../..", import.meta.url)),
      encoding: "utf8",
      env: {
        ...process.env,
        ORGMETRA_PERFORMANCE_TARGET_SHA: repositoryHead(),
        ORGMETRA_PERFORMANCE_DATA_FILE: fixture,
        ORGMETRA_PERFORMANCE_SUMMARY_FILE: summary,
        ORGMETRA_PERFORMANCE_BASE_URL: "http://127.0.0.1:1",
        ORGMETRA_PERFORMANCE_BEARER_TOKEN: "test-only-not-a-real-secret",
        ORGMETRA_PERFORMANCE_PROFILE: "first_commit",
      },
    });

    assert.notEqual(result.status, 0);
    assert.match(
      result.stderr,
      /performance fixture must not exceed 8388608 bytes/,
    );
    assert.doesNotMatch(result.stderr, /podman is required|preload the exact pinned k6 image/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
