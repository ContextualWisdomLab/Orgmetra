import assert from "node:assert/strict";
import test from "node:test";

import {
  hasGovernedSeparationJsonMediaType,
  hasGovernedSeparationNoStorePolicy,
  isGovernedSeparationConflict,
  isGovernedSeparationSuccess,
  parseGovernedSeparationResponseBody,
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

function conflictBody(overrides = {}) {
  return {
    error_code: "separation_conflict",
    message: "Refresh Employment and Assignment state, then retry.",
    next_action: "Refresh Employment and Assignment state, then retry.",
    support_reference: "err_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef",
    ...overrides,
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

test("rejects undeclared fields in the published success response envelope", () => {
  assert.equal(
    isGovernedSeparationSuccess(
      200,
      { ...successBody(false), extra: "undeclared" },
      { employmentRecordId: EMPLOYMENT, replayed: false },
    ),
    false,
  );
});

test("rejects sentinel separated-version identities in governed success evidence", () => {
  for (const separatedVersionId of [
    "00000000-0000-0000-0000-000000000000",
    "ffffffff-ffff-ffff-ffff-ffffffffffff",
  ]) {
    assert.equal(
      isGovernedSeparationSuccess(
        200,
        { ...successBody(false), separated_employment_record_version_id: separatedVersionId },
        { employmentRecordId: EMPLOYMENT, replayed: false },
      ),
      false,
    );
  }
});

test("rejects impossible success-response calendar timestamps", () => {
  const body = successBody(false);
  body.recorded_at = "2026-02-30T02:00:00Z";
  assert.equal(
    isGovernedSeparationSuccess(200, body, { employmentRecordId: EMPLOYMENT, replayed: false }),
    false,
  );
});

test("keeps success-response recorded_at inside the People datetime year domain", () => {
  for (const recordedAt of ["0001-01-01T00:00:00Z", "9999-12-31T23:59:59.999999Z"]) {
    assert.equal(
      isGovernedSeparationSuccess(
        200,
        { ...successBody(false), recorded_at: recordedAt },
        { employmentRecordId: EMPLOYMENT, replayed: false },
      ),
      true,
    );
  }
  assert.equal(
    isGovernedSeparationSuccess(
      200,
      { ...successBody(false), recorded_at: "0000-01-01T00:00:00Z" },
      { employmentRecordId: EMPLOYMENT, replayed: false },
    ),
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

test("accepts only one governed JSON response media type", () => {
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json" }), true);
  assert.equal(hasGovernedSeparationJsonMediaType({ "content-type": "Application/JSON; charset=utf-8" }), true);
  assert.equal(hasGovernedSeparationJsonMediaType({}), false);
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": "text/plain" }), false);
  assert.equal(
    hasGovernedSeparationJsonMediaType({
      "Content-Type": "application/json",
      "content-type": "application/json",
    }),
    false,
  );
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": ["application/json"] }), false);
});

test("requires the canonical no-store and Authorization-vary response policy", () => {
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": "no-store", Vary: "Authorization" }),
    true,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "cache-control": "No-Store", vary: "Accept-Encoding, authorization" }),
    true,
  );
  assert.equal(hasGovernedSeparationNoStorePolicy({ Vary: "Authorization" }), false);
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": "public, no-store", Vary: "Authorization" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": "no-store, s-maxage=60", Vary: "Authorization" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": "no-store", Vary: "Accept-Encoding" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": "no-store", Vary: "*" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({
      "Cache-Control": "no-store",
      "cache-control": "no-store",
      Vary: "Authorization",
    }),
    false,
  );
  assert.equal(
    hasGovernedSeparationNoStorePolicy({ "Cache-Control": ["no-store"], Vary: "Authorization" }),
    false,
  );
});

test("rejects k6-collapsed duplicate Content-Type values without rejecting quoted parameter commas", () => {
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; charset=utf-8, text/plain" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; profile=\"a,b\"" }),
    true,
  );
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; profile=\"a\\\",b\"" }),
    true,
  );
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; profile=\"unterminated, text/plain" }),
    false,
  );
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; profile=a\"b,c\"" }),
    false,
  );
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json;" }), false);
});

test("rejects invalid or duplicate media-type parameters", () => {
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; charset =utf-8" }), false);
  assert.equal(hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; charset= utf-8" }), false);
  assert.equal(
    hasGovernedSeparationJsonMediaType({ "Content-Type": "application/json; charset=utf-8; Charset=latin1" }),
    false,
  );
});

test("accepts only the published closed ErrorResponse shape for separation conflicts", () => {
  assert.equal(isGovernedSeparationConflict(409, conflictBody()), true);
  assert.equal(isGovernedSeparationConflict(409, { error: "separation_conflict" }), false);
  assert.equal(isGovernedSeparationConflict(409, { error_code: "separation_conflict" }), false);
  assert.equal(isGovernedSeparationConflict(409, conflictBody({ support_reference: "trace-123" })), false);
  assert.equal(isGovernedSeparationConflict(409, { ...conflictBody(), extra: "undeclared" }), false);
  assert.equal(isGovernedSeparationConflict(404, conflictBody()), false);
});

test("binds conflict support references to the canonical People token_urlsafe length", () => {
  assert.equal(isGovernedSeparationConflict(409, conflictBody()), true);
  for (const suffixLength of [24, 31, 33, 80]) {
    assert.equal(
      isGovernedSeparationConflict(409, conflictBody({ support_reference: `err_${"A".repeat(suffixLength)}` })),
      false,
    );
  }
});

test("bounds governed response JSON before strict parsing while preserving the closed error envelope", () => {
  const escapedBoundaryText = "\u0001".repeat(1000);
  const largestSemanticEnvelope = JSON.stringify(conflictBody({
    message: escapedBoundaryText,
    next_action: escapedBoundaryText,
  }));
  assert.ok(largestSemanticEnvelope.length < 16 * 1024);
  assert.deepEqual(
    parseGovernedSeparationResponseBody(largestSemanticEnvelope),
    JSON.parse(largestSemanticEnvelope),
  );

  const oversized = `${" ".repeat(16 * 1024)}${JSON.stringify(successBody(false))}`;
  assert.throws(
    () => parseGovernedSeparationResponseBody(oversized),
    /governed separation response body must not exceed 16384 UTF-8 bytes/,
  );
});

test("strict response parsing rejects duplicate trust-bearing JSON members before semantic validation", () => {
  assert.throws(
    () => parseGovernedSeparationResponseBody(`{"employment_record_id":"${EMPLOYMENT}","separated_employment_record_version_id":"${VERSION}","recorded_at":"2026-09-13T02:00:00Z","replayed":true,"replayed":false}`),
    /duplicate JSON object member name "replayed"/,
  );
  assert.throws(
    () => parseGovernedSeparationResponseBody('{"error_code":"separation_conflict","\\u0065rror_code":"separation_conflict"}'),
    /duplicate JSON object member name "error_code"/,
  );
});

test("strict response parsing preserves the published response object", () => {
  const body = successBody(false);
  assert.deepEqual(parseGovernedSeparationResponseBody(JSON.stringify(body)), body);
});