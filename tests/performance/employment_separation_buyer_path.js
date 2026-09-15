import http from "k6/http";
import crypto from "k6/crypto";
import { check, fail } from "k6";
import exec from "k6/execution";
import { Counter, Rate, Trend } from "k6/metrics";

import {
  parsePerformanceFixtureArtifact,
  requirePerformanceFixtureByteBudget,
} from "./employment_separation_fixture_artifact.mjs";
import {
  requestBody,
  requestHeaders,
  validatePerformanceFixture,
} from "./employment_separation_fixture_contract.mjs";
import { requirePinnedK6Runtime } from "./employment_separation_k6_runtime_contract.mjs";
import { normalizeEmploymentSeparationK6Summary } from "./employment_separation_k6_summary_contract.mjs";
import {
  isGovernedSeparationConflict,
  isGovernedSeparationSuccess,
  parseGovernedSeparationResponseBody,
} from "./employment_separation_response_contract.mjs";
import {
  PERFORMANCE_SUMMARY_TREND_STATS,
  approvedPerformanceLoadModel,
  arrivalRateScenarioForPerformanceProfile,
  requireDirectPerformanceClientNetwork,
  requirePerformanceProfile,
  thresholdsForPerformanceProfile,
} from "./employment_separation_run_contract.mjs";
import { buyerPathElapsedMs } from "./employment_separation_timing_contract.mjs";

const ROUTE = "/v1/employment-separations";
const MINIMUM_NON_CONTENDING_RECORDS = 1000;
const MINIMUM_CONTENTION_PAIRS = 100;
const TREND_BY_PROFILE = Object.freeze({
  first_commit: "employment_separation_first_commit_duration_ms",
  replay: "employment_separation_replay_duration_ms",
  rejection: "employment_separation_rejection_duration_ms",
  contention: "employment_separation_contention_duration_ms",
});
const fixturePath = __ENV.ORGMETRA_PERFORMANCE_DATA_FILE;
const baseUrl = (__ENV.ORGMETRA_PERFORMANCE_BASE_URL || "").replace(/\/$/, "");
const bearerToken = __ENV.ORGMETRA_PERFORMANCE_BEARER_TOKEN || "";
const targetSha = (__ENV.ORGMETRA_PERFORMANCE_TARGET_SHA || "").toLowerCase();
const selectedProfile = requirePerformanceProfile(__ENV.ORGMETRA_PERFORMANCE_PROFILE || "");
const clientNetworkTopology = requireDirectPerformanceClientNetwork(__ENV);
const k6Runtime = requirePinnedK6Runtime({
  version: __ENV.ORGMETRA_PERFORMANCE_K6_VERSION || "",
  image: __ENV.ORGMETRA_PERFORMANCE_K6_IMAGE || "",
  imageDigest: __ENV.ORGMETRA_PERFORMANCE_K6_IMAGE_DIGEST || "",
  runnerIdentity: __ENV.ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY || "",
});

if (!fixturePath) fail("ORGMETRA_PERFORMANCE_DATA_FILE is required");
if (!baseUrl) fail("ORGMETRA_PERFORMANCE_BASE_URL is required");
if (!bearerToken) fail("ORGMETRA_PERFORMANCE_BEARER_TOKEN is required and must not be stored in the fixture");
if (!/^[0-9a-f]{40}$/.test(targetSha)) fail("ORGMETRA_PERFORMANCE_TARGET_SHA must be a full Git commit SHA");

const fixtureBytes = open(fixturePath, "b");
requirePerformanceFixtureByteBudget(fixtureBytes);
const fixtureSha256 = crypto.sha256(fixtureBytes, "hex");
let fixtureDocument;
try { fixtureDocument = parsePerformanceFixtureArtifact(fixtureBytes); }
catch (error) { fail(error.message); }
const fixture = validatePerformanceFixture(fixtureDocument, {
  minimumNonContendingRecords: MINIMUM_NON_CONTENDING_RECORDS,
  minimumContentionPairs: MINIMUM_CONTENTION_PAIRS,
});
if (fixture.candidate_sha.toLowerCase() !== targetSha) fail("performance fixture candidate_sha does not match ORGMETRA_PERFORMANCE_TARGET_SHA");

const selectedRecords = fixture.profiles[selectedProfile];
const approvedLoadModel = approvedPerformanceLoadModel(selectedProfile);
const selectedScenario = arrivalRateScenarioForPerformanceProfile(selectedProfile, {
  expectedIterations: selectedRecords.length,
});

const firstCommitDuration = new Trend("employment_separation_first_commit_duration_ms", true);
const replayDuration = new Trend("employment_separation_replay_duration_ms", true);
const rejectionDuration = new Trend("employment_separation_rejection_duration_ms", true);
const contentionDuration = new Trend("employment_separation_contention_duration_ms", true);
const latencySamples = new Counter("employment_separation_latency_samples");
const unexpectedResponse = new Rate("employment_separation_unexpected_response");

export const options = {
  discardResponseBodies: false,
  scenarios: { [selectedProfile]: selectedScenario },
  thresholds: thresholdsForPerformanceProfile(selectedProfile, selectedRecords.length),
  summaryTrendStats: PERFORMANCE_SUMMARY_TREND_STATS,
};

function recordAt(profile) {
  const records = fixture.profiles[profile];
  const index = exec.scenario.iterationInTest;
  if (index < 0 || index >= records.length) fail(`${profile} iteration ${index} is outside the fixture`);
  return records[index];
}
function parseJson(response) {
  try { return parseGovernedSeparationResponseBody(response.body); }
  catch (_) { return null; }
}
function post(command, profile) {
  return http.post(`${baseUrl}${ROUTE}`, requestBody(command), { headers: requestHeaders(command, bearerToken), tags: { profile } });
}
function observe(response, trend, profile, predicate) {
  trend.add(buyerPathElapsedMs(response.timings), { profile });
  latencySamples.add(1, { profile });
  const passed = check(response, { [`${profile} returned the governed result`]: predicate });
  unexpectedResponse.add(!passed, { profile });
}

export function firstCommit() {
  const command = recordAt("first_commit");
  const response = post(command, "first_commit");
  observe(response, firstCommitDuration, "first_commit", (result) => isGovernedSeparationSuccess(result.status, parseJson(result), { employmentRecordId: command.payload.employment_record_id, replayed: false }));
}
export function replay() {
  const command = recordAt("replay");
  const response = post(command, "replay");
  observe(response, replayDuration, "replay", (result) => isGovernedSeparationSuccess(result.status, parseJson(result), { employmentRecordId: command.payload.employment_record_id, replayed: true }));
}
export function rejection() {
  const response = post(recordAt("rejection"), "rejection");
  observe(response, rejectionDuration, "rejection", (result) => isGovernedSeparationConflict(result.status, parseJson(result)));
}
export function contention() {
  const pair = recordAt("contention");
  const responses = http.batch([
    ["POST", `${baseUrl}${ROUTE}`, requestBody(pair.left), { headers: requestHeaders(pair.left, bearerToken), tags: { profile: "contention" } }],
    ["POST", `${baseUrl}${ROUTE}`, requestBody(pair.right), { headers: requestHeaders(pair.right, bearerToken), tags: { profile: "contention" } }],
  ]);
  for (const response of responses) { contentionDuration.add(buyerPathElapsedMs(response.timings), { profile: "contention" }); latencySamples.add(1, { profile: "contention" }); }
  const parsed = responses.map((response) => ({ status: response.status, body: parseJson(response) }));
  const successes = parsed.filter(({ status, body }) => isGovernedSeparationSuccess(status, body, { employmentRecordId: pair.left.payload.employment_record_id, replayed: false }));
  const conflicts = parsed.filter(({ status, body }) => isGovernedSeparationConflict(status, body));
  const passed = check(parsed, { "contention serializes one governed commit and one governed conflict": () => successes.length === 1 && conflicts.length === 1 });
  unexpectedResponse.add(!passed, { profile: "contention" });
}

export function handleSummary(data) {
  const normalizedK6 = normalizeEmploymentSeparationK6Summary(data, {
    expectedK6Version: k6Runtime.version,
    trendName: TREND_BY_PROFILE[selectedProfile],
  });
  const completedIterations = normalizedK6.metrics.iterations.values.count;
  const payload = {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: targetSha,
    fixture_sha256: fixtureSha256,
    k6_version: k6Runtime.version,
    k6_image: k6Runtime.image,
    k6_image_digest: k6Runtime.image_digest,
    k6_runner_identity: k6Runtime.runner_identity,
    selected_profile: selectedProfile,
    expected_iterations: selectedRecords.length,
    completed_iterations: completedIterations,
    sample_complete: completedIterations === selectedRecords.length,
    completed_at: new Date().toISOString(),
    load_model: { ...approvedLoadModel, client_network_topology: clientNetworkTopology },
    dataset_id: fixture.dataset_id,
    clearance_reference: fixture.clearance_reference,
    preparation_protocol_reference: fixture.preparation_protocol_reference,
    prepared_state_evidence_reference: fixture.prepared_state_evidence_reference,
    resource_evidence_reference: fixture.resource_evidence_reference,
    profile_preconditions: fixture.profile_preconditions,
    minimum_non_contending_records: MINIMUM_NON_CONTENDING_RECORDS,
    minimum_contention_pairs: MINIMUM_CONTENTION_PAIRS,
    k6: normalizedK6,
  };
  const rendered = `${JSON.stringify(payload, null, 2)}\n`;
  const path = __ENV.ORGMETRA_PERFORMANCE_SUMMARY_FILE || `employment-separation-performance-${selectedProfile}.json`;
  return { [path]: rendered, stdout: rendered };
}
