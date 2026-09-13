import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const acceptanceCheck = fileURLToPath(new URL("./employment_separation_acceptance_check.mjs", import.meta.url));

test("acceptance CLI rejects a result substituted after the runner digest receipt", () => {
  const temporaryRoot = mkdtempSync(join(tmpdir(), "orgmetra-runner-digest-"));
  try {
    const resultPath = join(temporaryRoot, "result.json");
    const runtimePath = join(temporaryRoot, "runtime.json");
    const fixturePath = join(temporaryRoot, "fixture.json");
    const originalResult = Buffer.from('{"schema_version":"orgmetra.original"}\n', "utf8");
    const substitutedResult = Buffer.from('{"schema_version":"orgmetra.substituted"}\n', "utf8");
    const runnerDigest = createHash("sha256").update(originalResult).digest("hex");

    writeFileSync(resultPath, substitutedResult, { mode: 0o600 });
    writeFileSync(runtimePath, "{}\n", { mode: 0o600 });
    writeFileSync(fixturePath, "{}\n", { mode: 0o600 });

    const result = spawnSync(
      process.execPath,
      [acceptanceCheck, resultPath, runtimePath, fixturePath, runnerDigest],
      { encoding: "utf8" },
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /runner result digest does not bind the supplied performance result/);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

test("acceptance CLI requires the runner digest handoff token", () => {
  const result = spawnSync(process.execPath, [acceptanceCheck, "result.json", "runtime.json", "fixture.json"], {
    encoding: "utf8",
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /<runner-result-sha256>/);
});
