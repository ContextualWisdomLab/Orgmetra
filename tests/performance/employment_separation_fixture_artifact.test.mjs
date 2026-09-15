import assert from "node:assert/strict";
import test from "node:test";

import {
  MAXIMUM_PERFORMANCE_FIXTURE_BYTES,
  parsePerformanceFixtureArtifact,
  requirePerformanceFixtureByteBudget,
} from "./employment_separation_fixture_artifact.mjs";

const MAXIMUM_BYTES = 8 * 1024 * 1024;

test("fixture byte budget is the governed 8 MiB ceiling", () => {
  assert.equal(MAXIMUM_PERFORMANCE_FIXTURE_BYTES, MAXIMUM_BYTES);
});

test("direct workload boundary rejects oversized fixture bytes before parsing", () => {
  const oversized = Buffer.alloc(MAXIMUM_BYTES + 1, 0x20);
  assert.throws(
    () => requirePerformanceFixtureByteBudget(oversized),
    /performance fixture must not exceed 8388608 bytes/,
  );
});

test("direct workload boundary rejects escaped-equivalent duplicate JSON member names", () => {
  const bytes = Buffer.from(
    '{"schema_version":"one","schema_\\u0076ersion":"two"}\n',
    "utf8",
  );
  assert.doesNotThrow(() => JSON.parse(bytes.toString("utf8")));
  assert.throws(
    () => parsePerformanceFixtureArtifact(bytes),
    /duplicate JSON object member name "schema_version"/,
  );
});

test("direct workload boundary preserves ordinary valid JSON objects", () => {
  assert.deepEqual(
    parsePerformanceFixtureArtifact(Buffer.from('{"profiles":{}}\n', "utf8")),
    { profiles: {} },
  );
});
