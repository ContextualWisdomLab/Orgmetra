import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { parseRuntimeEvidenceArtifact } from "./employment_separation_runtime_evidence_artifact.mjs";

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

test("binds acceptance runtime evidence to the exact raw artifact bytes", () => {
  const bytes = Buffer.from('{"schema_version":"orgmetra.employment_separation.runtime_evidence.v1"}\n', "utf8");
  const document = parseRuntimeEvidenceArtifact(bytes);

  assert.deepEqual(document.parsed, {
    schema_version: "orgmetra.employment_separation.runtime_evidence.v1",
  });
  assert.equal(document.sha256, sha256(bytes));
  assert.throws(
    () => parseRuntimeEvidenceArtifact(bytes.toString("utf8")),
    /runtime evidence must be supplied as raw bytes/,
  );
});

test("rejects byte-distinct malformed UTF-8 before lossy JSON interpretation can collapse it", () => {
  const prefix = Buffer.from('{"observer_reference":"observer:', "utf8");
  const suffix = Buffer.from('"}', "utf8");
  const first = Buffer.concat([prefix, Buffer.from([0x80]), suffix]);
  const second = Buffer.concat([prefix, Buffer.from([0x81]), suffix]);

  assert.equal(first.toString("utf8"), second.toString("utf8"));
  assert.notEqual(sha256(first), sha256(second));
  assert.doesNotThrow(() => JSON.parse(first.toString("utf8")));
  assert.doesNotThrow(() => JSON.parse(second.toString("utf8")));
  assert.throws(() => parseRuntimeEvidenceArtifact(first), /runtime evidence must be valid UTF-8/);
  assert.throws(() => parseRuntimeEvidenceArtifact(second), /runtime evidence must be valid UTF-8/);
});

test("rejects JSON values that are not runtime-evidence objects", () => {
  assert.throws(
    () => parseRuntimeEvidenceArtifact(Buffer.from("[]\n", "utf8")),
    /runtime evidence must be a JSON object/,
  );
  assert.throws(
    () => parseRuntimeEvidenceArtifact(Buffer.from("null\n", "utf8")),
    /runtime evidence must be a JSON object/,
  );
});
