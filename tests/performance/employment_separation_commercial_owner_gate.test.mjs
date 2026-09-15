import assert from "node:assert/strict";
import test from "node:test";

import { requireCommercialPerformanceAuthorities } from "./employment_separation_commercial_owner_gate.mjs";

const PERFORMANCE_ATTESTATION_GAP_PATTERN = /authenticated performance-evidence attestation.*ContextualWisdomLab\/.github#2162/;
const DEPLOYMENT_IDENTITY_GAP_PATTERN = /authenticated deployed-candidate evidence.*ContextualWisdomLab\/Orgmetra#395/;

test("reports every unresolved commercial evidence authority in one fail-closed result", () => {
  assert.throws(
    () => requireCommercialPerformanceAuthorities(),
    (error) => {
      assert.match(error.message, PERFORMANCE_ATTESTATION_GAP_PATTERN);
      assert.match(error.message, DEPLOYMENT_IDENTITY_GAP_PATTERN);
      return true;
    },
  );
});
