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

export const PERFORMANCE_CLIENT_NETWORK_TOPOLOGY = "direct_no_client_mitm_proxy";

const EXEC_BY_PROFILE = Object.freeze({
  first_commit: "firstCommit",
  replay: "replay",
  rejection: "rejection",
  contention: "contention",
});
const APPROVED_LOAD_BY_PROFILE = Object.freeze({
  first_commit: Object.freeze({ target_rps: 20, duration_seconds: 50, preallocated_vus: 20, max_vus: 80 }),
  replay: Object.freeze({ target_rps: 20, duration_seconds: 50, preallocated_vus: 20, max_vus: 80 }),
  rejection: Object.freeze({ target_rps: 20, duration_seconds: 50, preallocated_vus: 20, max_vus: 80 }),
  contention: Object.freeze({ target_rps: 10, duration_seconds: 10, preallocated_vus: 20, max_vus: 80 }),
});
const PROXY_ENVIRONMENT_KEYS = Object.freeze([
  "HTTP_PROXY",
  "HTTPS_PROXY",
  "ALL_PROXY",
  "http_proxy",
  "https_proxy",
  "all_proxy",
]);

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

export function approvedPerformanceLoadModel(profile) {
  const selectedProfile = requirePerformanceProfile(profile);
  const approved = APPROVED_LOAD_BY_PROFILE[selectedProfile];
  return Object.freeze({
    executor: "constant-arrival-rate",
    target_rps: approved.target_rps,
    duration_seconds: approved.duration_seconds,
    preallocated_vus: approved.preallocated_vus,
    max_vus: approved.max_vus,
    client_network_topology: PERFORMANCE_CLIENT_NETWORK_TOPOLOGY,
  });
}

export function requireDirectPerformanceClientNetwork(environment) {
  if (environment === null || typeof environment !== "object" || Array.isArray(environment)) {
    throw new Error("performance client environment must be an object");
  }
  const configuredProxy = PROXY_ENVIRONMENT_KEYS.find((key) => (
    typeof environment[key] === "string" && environment[key].trim() !== ""
  ));
  if (configuredProxy) {
    throw new Error(`${configuredProxy} must be unset for commercial timing acceptance`);
  }
  return PERFORMANCE_CLIENT_NETWORK_TOPOLOGY;
}

export function requireVerifiedTlsTransport(insecureSkipTlsVerify) {
  if (insecureSkipTlsVerify !== false) {
    throw new Error("TLS certificate verification must remain enabled for commercial timing acceptance");
  }
  return insecureSkipTlsVerify;
}

export function validatePerformanceLoadModel(value, expectedIterations, profile) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("load_model must be an object");
  }
  const expectedKeys = [
    "executor",
    "target_rps",
    "duration_seconds",
    "preallocated_vus",
    "max_vus",
    "client_network_topology",
  ].sort();
  const actualKeys = Object.keys(value).sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    throw new Error(`load_model must contain exactly ${expectedKeys.join(", ")}`);
  }
  if (value.executor !== "constant-arrival-rate") {
    throw new Error("load_model.executor must be constant-arrival-rate");
  }
  if (value.client_network_topology !== PERFORMANCE_CLIENT_NETWORK_TOPOLOGY) {
    throw new Error(`load_model.client_network_topology must be ${PERFORMANCE_CLIENT_NETWORK_TOPOLOGY}`);
  }
  const iterations = positiveInteger(expectedIterations, "expectedIterations");
  const selectedProfile = requirePerformanceProfile(profile);
  const rate = positiveInteger(value.target_rps, "load_model.target_rps");
  const duration = positiveInteger(value.duration_seconds, "load_model.duration_seconds");
  const preAllocated = positiveInteger(value.preallocated_vus, "load_model.preallocated_vus");
  const maximum = positiveInteger(value.max_vus, "load_model.max_vus");
  if (maximum < preAllocated) {
    throw new Error("load_model.max_vus must be greater than or equal to load_model.preallocated_vus");
  }
  const approved = approvedPerformanceLoadModel(selectedProfile);
  for (const field of ["target_rps", "duration_seconds", "preallocated_vus", "max_vus"]) {
    if (value[field] !== approved[field]) {
      throw new Error(`load_model.${field} must match the approved ${selectedProfile} load model`);
    }
  }
  const scheduledIterations = rate * duration;
  if (!Number.isSafeInteger(scheduledIterations) || scheduledIterations !== iterations) {
    throw new Error("load_model target_rps * duration_seconds must equal expectedIterations exactly");
  }
  return approved;
}

export function arrivalRateScenarioForPerformanceProfile(profile, { expectedIterations }) {
  const selectedProfile = requirePerformanceProfile(profile);
  const approved = approvedPerformanceLoadModel(selectedProfile);
  const loadModel = validatePerformanceLoadModel(approved, expectedIterations, selectedProfile);
  return {
    executor: loadModel.executor,
    exec: EXEC_BY_PROFILE[selectedProfile],
    rate: loadModel.target_rps,
    timeUnit: "1s",
    duration: `${loadModel.duration_seconds}s`,
    preAllocatedVUs: loadModel.preallocated_vus,
    maxVUs: loadModel.max_vus,
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
    iterations: [`count>=${expectedIterations}`],
  };
  if (profile === "first_commit") {
    thresholds.employment_separation_first_commit_duration_ms = ["p(95)<=20"];
  }
  return thresholds;
}
