import assert from "node:assert/strict";
import test from "node:test";

import { governedSeparationRequestParams } from "./employment_separation_request_contract.mjs";

const headers = Object.freeze({
  Authorization: "Bearer performance-token",
  "Content-Type": "application/json",
  "Idempotency-Key": "employment-separation-0001",
  "X-Actor-Reference": "worker:performance-operator",
  "X-Purpose-Code": "workforce_admin",
  "X-Tenant-Reference": "10000000-0000-4000-8000-000000000001",
});

test("governed request params disable redirects without changing the request headers", () => {
  const params = governedSeparationRequestParams(headers, "first_commit");

  assert.equal(params.redirects, 0);
  assert.strictEqual(params.headers, headers);
  assert.deepEqual(params.tags, { profile: "first_commit" });
  assert.deepEqual(Object.keys(params).sort(), ["headers", "redirects", "tags"]);
});

test("governed request params apply the same no-redirect policy to every buyer profile", () => {
  for (const profile of ["first_commit", "replay", "rejection", "contention"]) {
    const params = governedSeparationRequestParams(headers, profile);
    assert.equal(params.redirects, 0, `${profile} must not follow redirects`);
    assert.deepEqual(params.tags, { profile });
  }
});

test("governed request params reject unknown profiles", () => {
  assert.throws(
    () => governedSeparationRequestParams(headers, "redirected_success"),
    /unsupported Employment-separation performance profile/,
  );
});

test("governed request params reject non-object headers", () => {
  for (const invalid of [null, [], "Authorization: Bearer token"] ) {
    assert.throws(
      () => governedSeparationRequestParams(invalid, "first_commit"),
      /request headers must be a plain object/,
    );
  }
});
