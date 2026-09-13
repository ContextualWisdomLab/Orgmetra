import assert from "node:assert/strict";
import test from "node:test";

import {
  PINNED_K6_VERSION,
  requirePinnedK6Version,
} from "./employment_separation_k6_runtime_contract.mjs";

test("accepts only the repository-pinned k6 runtime", () => {
  assert.equal(PINNED_K6_VERSION, "2.2.0");
  assert.equal(requirePinnedK6Version("2.2.0"), "2.2.0");
});

test("rejects missing, older, newer, or decorated k6 runtime declarations", () => {
  for (const value of ["", "2.1.0", "2.2.1", "2.3.0", "v2.2.0", "2.2.0-dev"]) {
    assert.throws(
      () => requirePinnedK6Version(value),
      /require k6 2\.2\.0/,
    );
  }
});
