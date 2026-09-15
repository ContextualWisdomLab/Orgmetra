import assert from "node:assert/strict";
import test from "node:test";

import {
  isGovernedSeparationConflict,
  isGovernedSeparationSuccess,
} from "./employment_separation_response_contract.mjs";

const EMPLOYMENT = "30000000-0000-4000-8000-000000000001";
const VERSION = "50000000-0000-4000-8000-000000000001";

function successBody(replayed = false) {
  return {
    employment_record_id: EMPLOYMENT,
    separated_employment_record_version_id: VERSION,
    recorded_at: "2026-09-13T02:00:00Z",
    replayed,
  };
}

test("accepts the published first-commit and replay response shape", () => {
  assert.equal(
    isGovernedSeparationSuccess(200, successBody(false), { employmentRecordId: EMPLOYMENT, replayed: false }),
    true,
  );
  assert.equal(
    isGovernedSeparationSuccess(200, successBody(true), { employmentRecordId: EMPLOYMENT, replayed: true }),
    true,
  );
});

test("rejects impossible success-response calendar timestamps", () => {
  const body = successBody(false);
  body.recorded_at = "2026-02-30T02:00:00Z";
  assert.equal(
    isGovernedSeparationSuccess(200, body, { employmentRecordId: EMPLOYMENT, replayed: false }),
    false,
  );
});

test("rejects success responses that are replay- or target-inconsistent", () => {
  assert.equal(
    isGovernedSeparationSuccess(200, successBody(true), { employmentRecordId: EMPLOYMENT, replayed: false }),
    false,
  );
  assert.equal(
    isGovernedSeparationSuccess(200, successBody(false), {
      employmentRecordId: "30000000-0000-4000-8000-000000000002",
      replayed: false,
    }),
    false,
  );
});

test("uses the published conflict error field rather than an invented error_code field", () => {
  assert.equal(isGovernedSeparationConflict(409, { error: "separation_conflict" }), true);
  assert.equal(isGovernedSeparationConflict(409, { error_code: "separation_conflict" }), false);
  assert.equal(isGovernedSeparationConflict(404, { error: "separation_conflict" }), false);
});