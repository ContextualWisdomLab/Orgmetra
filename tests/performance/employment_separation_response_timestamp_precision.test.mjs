import assert from "node:assert/strict";
import test from "node:test";

import { isGovernedSeparationSuccess } from "./employment_separation_response_contract.mjs";

const EMPLOYMENT = "30000000-0000-4000-8000-000000000001";
const VERSION = "50000000-0000-4000-8000-000000000001";

function successBody(recordedAt) {
  return {
    employment_record_id: EMPLOYMENT,
    separated_employment_record_version_id: VERSION,
    recorded_at: recordedAt,
    replayed: false,
  };
}

function accepted(recordedAt) {
  return isGovernedSeparationSuccess(200, successBody(recordedAt), {
    employmentRecordId: EMPLOYMENT,
    replayed: false,
  });
}

test("accepts only recorded_at precision emitted by canonical People datetime serialization", () => {
  for (const recordedAt of [
    "2026-09-13T02:00:00Z",
    "2026-09-13T02:00:00.1Z",
    "2026-09-13T02:00:00.123456Z",
  ]) {
    assert.equal(accepted(recordedAt), true, recordedAt);
  }

  assert.equal(accepted("2026-09-13T02:00:00.1234567Z"), false);
  assert.equal(accepted(`2026-09-13T02:00:00.${"1".repeat(17000)}Z`), false);
});
