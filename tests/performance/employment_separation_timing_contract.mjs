function fail(message) {
  throw new Error(message);
}

function finiteNonNegative(value, label) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    fail(`${label} must be a finite non-negative number`);
  }
  return value;
}

export function buyerPathElapsedMs(timings) {
  if (timings === null || typeof timings !== "object" || Array.isArray(timings)) {
    fail("response.timings must be an object");
  }

  const blocked = finiteNonNegative(timings.blocked, "response.timings.blocked");
  finiteNonNegative(timings.connecting, "response.timings.connecting");
  finiteNonNegative(timings.tls_handshaking, "response.timings.tls_handshaking");
  const duration = finiteNonNegative(timings.duration, "response.timings.duration");

  // k6 v2.2 computes blocked from GetConn to GotConn, so TCP connect and TLS
  // handshake are nested inside blocked for a new direct connection. Duration is
  // the later sending + waiting + receiving interval. Adding connecting/TLS again
  // would double-count cold-connection latency and could create a false RED.
  return blocked + duration;
}
