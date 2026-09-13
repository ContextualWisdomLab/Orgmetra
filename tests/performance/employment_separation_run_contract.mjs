export const PERFORMANCE_PROFILES = Object.freeze([
  "first_commit",
  "replay",
  "rejection",
  "contention",
]);

export const PERFORMANCE_SUMMARY_TREND_STATS = Object.freeze([
  "p(50)",
  "p(95)",
  "p(99)",
  "max",
]);

export function requirePerformanceProfile(value) {
  if (typeof value !== "string" || !PERFORMANCE_PROFILES.includes(value)) {
    throw new Error(`ORGMETRA_PERFORMANCE_PROFILE must be exactly one of: ${PERFORMANCE_PROFILES.join(", ")}`);
  }
  return value;
}

export function thresholdsForPerformanceProfile(profile, expectedIterations) {
  requirePerformanceProfile(profile);
  if (!Number.isSafeInteger(expectedIterations) || expectedIterations < 1) {
    throw new Error("expectedIterations must be a positive safe integer");
  }
  const expectedLatencySamples = profile === "contention" ? expectedIterations * 2 : expectedIterations;
  if (!Number.isSafeInteger(expectedLatencySamples)) {
    throw new Error("expected latency sample count must be a positive safe integer");
  }
  const thresholds = {
    employment_separation_unexpected_response: ["rate==0"],
    employment_separation_latency_samples: [`count>=${expectedLatencySamples}`],
    checks: ["rate==1"],
    iterations: [`count>=${expectedIterations}`],
  };
  if (profile === "first_commit") {
    thresholds.employment_separation_first_commit_duration_ms = ["p(95)<=20"];
  }
  return thresholds;
}
