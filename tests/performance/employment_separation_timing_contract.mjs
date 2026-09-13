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
  const connecting = finiteNonNegative(timings.connecting, "response.timings.connecting");
  const tlsHandshaking = finiteNonNegative(timings.tls_handshaking, "response.timings.tls_handshaking");
  const duration = finiteNonNegative(timings.duration, "response.timings.duration");

  // k6 documents duration as sending + waiting + receiving. TCP setup and TLS
  // negotiation are separate phases, while blocked also carries pre-request wait
  // such as connection-slot/DNS work. Final commercial acceptance disallows a
  // client-side HTTPS MITM proxy because k6 can overlap these phases in the
  // unusual double-TLS topology documented upstream.
  return blocked + connecting + tlsHandshaking + duration;
}
