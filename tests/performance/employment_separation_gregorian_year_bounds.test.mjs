import assert from "node:assert/strict";
import test from "node:test";

import { acceptanceFixture } from "./employment_separation_acceptance_fixture_test_support.mjs";
import { validatePerformanceFixture } from "./employment_separation_fixture_contract.mjs";

const smallAcceptance = { minimumNonContendingRecords: 1, minimumContentionPairs: 1 };

function smallFixture() {
  const value = acceptanceFixture();
  value.profiles.first_commit = value.profiles.first_commit.slice(0, 1);
  value.profiles.replay = value.profiles.replay.slice(0, 1);
  value.profiles.rejection = value.profiles.rejection.slice(0, 1);
  value.profiles.contention = value.profiles.contention.slice(0, 1);
  return value;
}

test("accepts the earliest People business date without ECMAScript year normalization", () => {
  const value = smallFixture();
  value.profiles.first_commit[0].payload.separation_effective_on = "0001-01-01";
  assert.doesNotThrow(() => validatePerformanceFixture(value, smallAcceptance));
});

test("accepts the latest People business date in the four-digit contract", () => {
  const value = smallFixture();
  value.profiles.first_commit[0].payload.separation_effective_on = "9999-12-31";
  assert.doesNotThrow(() => validatePerformanceFixture(value, smallAcceptance));
});

test("rejects year zero in People business dates", () => {
  const value = smallFixture();
  value.profiles.first_commit[0].payload.separation_effective_on = "0000-01-01";
  assert.throws(
    () => validatePerformanceFixture(value, smallAcceptance),
    /separation_effective_on must be an RFC 3339 full-date/,
  );
});

test("accepts the governed UTC timestamp year boundaries", () => {
  for (const preparedAt of ["0001-01-01T00:00:00Z", "9999-12-31T23:59:59.999999Z"]) {
    const value = smallFixture();
    value.prepared_at = preparedAt;
    assert.doesNotThrow(() => validatePerformanceFixture(value, smallAcceptance));
  }
});

test("rejects year zero in governed UTC evidence timestamps", () => {
  const value = smallFixture();
  value.prepared_at = "0000-01-01T00:00:00Z";
  assert.throws(
    () => validatePerformanceFixture(value, smallAcceptance),
    /fixture.prepared_at must be an RFC 3339 UTC timestamp/,
  );
});
