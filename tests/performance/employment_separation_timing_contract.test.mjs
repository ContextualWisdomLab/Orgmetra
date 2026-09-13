import assert from "node:assert/strict";
import test from "node:test";

import { buyerPathElapsedMs } from "./employment_separation_timing_contract.mjs";

test("includes connection acquisition in the buyer-path elapsed time", () => {
  assert.equal(buyerPathElapsedMs({ blocked: 6.5, duration: 14.5 }), 21);
});

test("does not double count connecting or TLS fields already represented by blocked", () => {
  assert.equal(buyerPathElapsedMs({
    blocked: 6,
    connecting: 2,
    tls_handshaking: 3,
    duration: 10,
  }), 16);
});

test("preserves keep-alive requests whose blocked phase is effectively zero", () => {
  assert.equal(buyerPathElapsedMs({ blocked: 0.4, duration: 9.6 }), 10);
});

test("rejects missing, negative, or non-finite timing evidence", () => {
  for (const timings of [
    null,
    [],
    {},
    { blocked: -1, duration: 10 },
    { blocked: 1, duration: -1 },
    { blocked: Number.NaN, duration: 10 },
    { blocked: 1, duration: Number.POSITIVE_INFINITY },
  ]) {
    assert.throws(() => buyerPathElapsedMs(timings), /timings|finite non-negative/);
  }
});
