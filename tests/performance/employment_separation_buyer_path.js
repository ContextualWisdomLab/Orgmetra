import http from "k6/http";
import { check, fail } from "k6";
import exec from "k6/execution";
import { Rate, Trend } from "k6/metrics";

import {
  requestBody,
  requestHeaders,
  validatePerformanceFixture,
} from "./employment_separation_fixture_contract.mjs";
import {
  isGovernedSeparationConflict,
  isGovernedSeparationSuccess,
} from "./employment_separation_response_contract.mjs";

const ROUTE = "/v1/employment-separations";
const MINIMUM_NON_CONTENDING_RECORDS = 1000;
const MINIMUM_CONTENTION_PAIRS = 100;
const fixturePath = __ENV.ORGMETRA_PERFORMANCE_DATA_FILE;
const baseUrl = (__ENV.ORGMETRA_PERFORMANCE_BASE_URL || "").replace(/\/$/, "");
const bearerToken = __ENV.ORGMETRA_PERFORMANCE_BEARER_TOKEN || "";
const targetSha = (__ENV.ORGMETRA_PERFORMANCE_TARGET_SHA || "").toLowerCase();

if (!fixturePath) fail("ORGMETRA_PERFORMANCE_DATA_FILE is required");
if (!baseUrl) fail("ORGMETRA_PERFORMANCE_BASE_URL is required");
if (!bearerToken) fail("ORGMETRA_PERFORMANCE_BEARER_TOKEN is required and must not be stored in the fixture");
if (!/^[0-9a-f]{40}$/.test(targetSha)) fail("ORGMETRA_PERFORMANCE_TARGET_SHA must be a full Git commit SHA");

const fixture = validatePerformanceFixture(JSON.parse(open(fixturePath)), {
  minimumNonContendingRecords: MINIMUM_NON_CONTENDING_RECORDS,
  minimumContentionPairs: MINIMUM_CONTENTION_PAIRS,
});
if (fixture.candidate_sha.toLowerCase() !== targetSha) {
  fail("performance fixture candidate_sha does not match ORGMETRA_PERFORMANCE_TARGET_SHA");
}

function integerSetting(name, fallback, maximum) {
  const raw = __ENV[name];
  if (raw === undefined || raw === "") return Math.min(fallback, maximum);
  if (!/^\d+$/.test(raw)) fail(`${name} must be a positive integer`);
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > maximum) {
    fail(`${name} must be between 1 and ${maximum}`);
  }
  return value;
}

const nonContendingVus = integerSetting("ORGMETRA_PERFORMANCE_VUS", 20, fixture.profiles.first_commit.length);
const contentionVus = integerSetting("ORGMETRA_PERFORMANCE_CONTENTION_VUS", 10, fixture.profiles.contention.length);

const firstCommitDuration = new Trend("employment_separation_first_commit_duration_ms", true);
const replayDuration = new Trend("employment_separation_replay_duration_ms", true);
const rejectionDuration = new Trend("employment_separation_rejection_duration_ms", true);
const contentionDuration = new Trend("employment_separation_contention_duration_ms", true);
const unexpectedResponse = new Rate("employment_separation_unexpected_response");

export const options = {
  discardResponseBodies: false,
  scenarios: {
    first_commit: {
      executor: "shared-iterations",
      exec: "firstCommit",
      iterations: fixture.profiles.first_commit.length,
      vus: nonContendingVus,
      maxDuration: "30m",
      gracefulStop: "0s",
    },
    replay: {
      executor: "shared-iterations",
      exec: "replay",
      iterations: fixture.profiles.replay.length,
      vus: nonContendingVus,
      maxDuration: "30m",
      gracefulStop: "0s",
    },
    rejection: {
      executor: "shared-iterations",
      exec: "rejection",
      iterations: fixture.profiles.rejection.length,
      vus: nonContendingVus,
      maxDuration: "30m",
      gracefulStop: "0s",
    },
    contention: {
      executor: "shared-iterations",
      exec: "contention",
      iterations: fixture.profiles.contention.length,
      vus: contentionVus,
      maxDuration: "30m",
      gracefulStop: "0s",
    },
  },
  thresholds: {
    employment_separation_first_commit_duration_ms: ["p(95)<=20"],
    employment_separation_unexpected_response: ["rate==0"],
    checks: ["rate==1"],
  },
};

function recordAt(profile) {
  const records = fixture.profiles[profile];
  const index = exec.scenario.iterationInTest;
  if (index < 0 || index >= records.length) fail(`${profile} iteration ${index} is outside the fixture`);
  return records[index];
}

function parseJson(response) {
  try {
    return response.json();
  } catch (_) {
    return null;
  }
}

function post(command, profile) {
  return http.post(`${baseUrl}${ROUTE}`, requestBody(command), {
    headers: requestHeaders(command, bearerToken),
    tags: { profile },
  });
}

function observe(response, trend, profile, predicate) {
  trend.add(response.timings.duration, { profile });
  const passed = check(response, {
    [`${profile} returned the governed result`]: predicate,
  });
  unexpectedResponse.add(!passed, { profile });
}

export function firstCommit() {
  const command = recordAt("first_commit");
  const response = post(command, "first_commit");
  observe(response, firstCommitDuration, "first_commit", (result) => (
    isGovernedSeparationSuccess(result.status, parseJson(result), {
      employmentRecordId: command.payload.employment_record_id,
      replayed: false,
    })
  ));
}

export function replay() {
  const command = recordAt("replay");
  const response = post(command, "replay");
  observe(response, replayDuration, "replay", (result) => (
    isGovernedSeparationSuccess(result.status, parseJson(result), {
      employmentRecordId: command.payload.employment_record_id,
      replayed: true,
    })
  ));
}

export function rejection() {
  const response = post(recordAt("rejection"), "rejection");
  observe(response, rejectionDuration, "rejection", (result) => (
    isGovernedSeparationConflict(result.status, parseJson(result))
  ));
}

export function contention() {
  const pair = recordAt("contention");
  const responses = http.batch([
    ["POST", `${baseUrl}${ROUTE}`, requestBody(pair.left), { headers: requestHeaders(pair.left, bearerToken), tags: { profile: "contention" } }],
    ["POST", `${baseUrl}${ROUTE}`, requestBody(pair.right), { headers: requestHeaders(pair.right, bearerToken), tags: { profile: "contention" } }],
  ]);
  for (const response of responses) contentionDuration.add(response.timings.duration, { profile: "contention" });
  const parsed = responses.map((response) => ({ status: response.status, body: parseJson(response) }));
  const successes = parsed.filter(({ status, body }) => (
    isGovernedSeparationSuccess(status, body, {
      employmentRecordId: pair.left.payload.employment_record_id,
      replayed: false,
    })
  ));
  const conflicts = parsed.filter(({ status, body }) => isGovernedSeparationConflict(status, body));
  const passed = check(parsed, {
    "contention serializes one governed commit and one governed conflict": () => successes.length === 1 && conflicts.length === 1,
  });
  unexpectedResponse.add(!passed, { profile: "contention" });
}

export function handleSummary(data) {
  const payload = {
    schema_version: "orgmetra.employment_separation.performance_result.v1",
    candidate_sha: targetSha,
    dataset_id: fixture.dataset_id,
    clearance_reference: fixture.clearance_reference,
    preparation_protocol_reference: fixture.preparation_protocol_reference,
    prepared_state_evidence_reference: fixture.prepared_state_evidence_reference,
    resource_evidence_reference: fixture.resource_evidence_reference,
    profile_preconditions: fixture.profile_preconditions,
    minimum_non_contending_records: MINIMUM_NON_CONTENDING_RECORDS,
    minimum_contention_pairs: MINIMUM_CONTENTION_PAIRS,
    k6: data,
  };
  const rendered = `${JSON.stringify(payload, null, 2)}\n`;
  const path = __ENV.ORGMETRA_PERFORMANCE_SUMMARY_FILE || "employment-separation-performance-result.json";
  return { [path]: rendered, stdout: rendered };
}
