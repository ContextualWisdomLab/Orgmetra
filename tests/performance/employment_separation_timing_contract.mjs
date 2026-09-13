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
  const duration = finiteNonNegative(timings.duration, "response.timings.duration");

  // k6 http_req_duration excludes connection acquisition. `blocked + duration`
  // preserves the observed client-side request elapsed time without separately
  // adding connecting/TLS phases that can already be contained in `blocked`.
  return blocked + duration;
}
