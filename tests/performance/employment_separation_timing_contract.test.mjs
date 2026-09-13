import assert from "node:assert/strict";
import test from "node:test";

import { buyerPathElapsedMs } from "./employment_separation_timing_contract.mjs";

test("includes blocked, TCP, TLS, and request phases in buyer-path elapsed time", () => {
  assert.equal(buyerPathElapsedMs({
    blocked: 1.5,
    connecting: 2.5,
    tls_handshaking: 3,
    duration: 14,
  }), 21);
});

test("preserves keep-alive requests when connection phases are zero", () => {
  assert.equal(buyerPathElapsedMs({
    blocked: 0.4,
    connecting: 0,
    tls_handshaking: 0,
    duration: 9.6,
  }), 10);
});

test("does not drop TCP or TLS latency from a cold request", () => {
  assert.equal(buyerPathElapsedMs({
    blocked: 1,
    connecting: 4,
    tls_handshaking: 5,
    duration: 10,
  }), 20);
});

test("rejects missing, negative, or non-finite timing evidence", () => {
  for (const timings of [
    null,
    [],
    {},
    { blocked: 1, connecting: 2, tls_handshaking: 3 },
    { blocked: -1, connecting: 2, tls_handshaking: 3, duration: 10 },
    { blocked: 1, connecting: -1, tls_handshaking: 3, duration: 10 },
    { blocked: 1, connecting: 2, tls_handshaking: -1, duration: 10 },
    { blocked: 1, connecting: 2, tls_handshaking: 3, duration: -1 },
    { blocked: Number.NaN, connecting: 2, tls_handshaking: 3, duration: 10 },
    { blocked: 1, connecting: 2, tls_handshaking: 3, duration: Number.POSITIVE_INFINITY },
  ]) {
    assert.throws(() => buyerPathElapsedMs(timings), /timings|finite non-negative/);
  }
});
