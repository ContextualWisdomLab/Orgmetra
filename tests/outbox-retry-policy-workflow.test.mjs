import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const workflow = readFileSync(
  new URL("../.github/workflows/outbox-retry-policy-quality.yml", import.meta.url),
  "utf8",
);

test("outbox retry policy quality runs for develop and its stacked parent base", () => {
  assert.match(
    workflow,
    /pull_request:\s*\n\s*branches:\s*\n\s*- develop\s*\n\s*- docs\/protected-truth-refresh(?:\s|$)/,
  );
});
