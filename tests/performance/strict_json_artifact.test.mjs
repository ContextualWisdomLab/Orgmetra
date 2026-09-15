import assert from "node:assert/strict";
import test from "node:test";

import { parseStrictJsonText } from "./strict_json_artifact.mjs";

function nestedArray(depth) {
  return `${"[".repeat(depth)}0${"]".repeat(depth)}`;
}

test("accepts JSON evidence at the declared nesting boundary", () => {
  assert.doesNotThrow(() => parseStrictJsonText(nestedArray(64), "evidence"));
});

test("rejects JSON evidence beyond the declared nesting boundary", () => {
  assert.throws(
    () => parseStrictJsonText(nestedArray(65), "evidence"),
    /maximum JSON nesting depth 64/,
  );
});
