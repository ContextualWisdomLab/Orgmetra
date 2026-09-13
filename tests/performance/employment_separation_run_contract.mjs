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
  "count",
]);

const EXEC_BY_PROFILE = Object.freeze({
  first_commit: "firstCommit",
  replay: "replay",
  rejection: "rejection",
  contention: "contention",
});

export function requirePerformanceProfile(value) {
  if (typeof value !== "string" || !PERFORMANCE_PROFILES.includes(value)) {
    throw new Error(`ORGMETRA_PERFORMANCE_PROFILE must be exactly one of: ${PERFORMANCE_PROFILES.join(", ")}`);
  }
  return value;
}

function positiveInteger(value, label) {
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new Error(`${label} must be a positive safe integer`);
  }
  return value;
}

export function arrivalRateScenarioForPerformanceProfile(profile, {
  expectedIterations,
  targetRps,
  durationSeconds,
  preAllocatedVUs,
  maxVUs,
}) {
  requirePerformanceProfile(profile);
  const iterations = positiveInteger(expectedIterations, "expectedIterations");
  const rate = positiveInteger(targetRps, "targetRps");
  const duration = positiveInteger(durationSeconds, "durationSeconds");
  const preAllocated = positiveInteger(preAllocatedVUs, "preAllocatedVUs");
  const maximum = positiveInteger(maxVUs, "maxVUs");
  if (maximum < preAllocated) {
    throw new Error("maxVUs must be greater than or equal to preAllocatedVUs");
  }
  const scheduledIterations = rate * duration;
  if (!Number.isSafeInteger(scheduledIterations) || scheduledIterations !== iterations) {
    throw new Error("targetRps * durationSeconds must equal the selected fixture iteration count exactly");
  }
  return {
    executor: "constant-arrival-rate",
    exec: EXEC_BY_PROFILE[profile],
    rate,
    timeUnit: "1s",
    duration: `${duration}s`,
    preAllocatedVUs: preAllocated,
    maxVUs: maximum,
    gracefulStop: "30s",
  };
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
    dropped_iterations: ["count==0"],
    iterations: [`count>=${expectedIterations}`],
  };
  if (profile === "first_commit") {
    thresholds.employment_separation_first_commit_duration_ms = ["p(95)<=20"];
  }
  return thresholds;
}
