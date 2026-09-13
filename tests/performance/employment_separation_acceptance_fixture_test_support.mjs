import { createHash } from "node:crypto";

export const ACCEPTANCE_CANDIDATE_SHA = "a".repeat(40);
export const ACCEPTANCE_PROFILE_PRECONDITIONS = Object.freeze({
  first_commit: "active_current_expected_version",
  replay: "same_key_same_semantics_already_committed",
  rejection: "expected_version_stale_or_semantic_conflict",
  contention: "active_current_expected_version",
});

function uuid(value) {
  const tail = value.toString(16).padStart(12, "0");
  return `00000000-0000-4000-8000-${tail}`;
}

function command(index, keySuffix = "only") {
  return {
    actor_reference: `actor:perf${index}`,
    idempotency_key: `employment-separation-perf-${index}-${keySuffix}`,
    tenant_record_id: uuid(900000),
    payload: {
      confirmation_reference: `confirmation:perf${index}`,
      employment_record_id: uuid(100000 + index),
      evidence_reference: `evidence:perf${index}`,
      evidence_version_code: "v1",
      expected_employment_record_version_id: uuid(500000 + index),
      person_record_id: uuid(300000 + index),
      separation_effective_on: "2026-09-01",
      separation_reason_code: "voluntary_resignation",
    },
  };
}

function records(start, count) {
  return Array.from({ length: count }, (_, offset) => command(start + offset));
}

export function acceptanceFixture({ rightCleared = true, synthetic = false } = {}) {
  const contentionStart = 4000;
  return {
    candidate_sha: ACCEPTANCE_CANDIDATE_SHA,
    clearance_reference: "data_clearance:perf-2026-09",
    dataset_id: "dataset:employment-separation-perf-1",
    prepared_at: "2026-09-13T04:00:00Z",
    prepared_state_evidence_reference: "evidence:prepared-state-perf-1",
    preparation_protocol_reference: "protocol:employment-separation-perf-v1",
    profile_preconditions: { ...ACCEPTANCE_PROFILE_PRECONDITIONS },
    profiles: {
      first_commit: records(1, 1000),
      replay: records(1001, 1000),
      rejection: records(2001, 1000),
      contention: Array.from({ length: 100 }, (_, offset) => {
        const index = contentionStart + offset;
        return {
          left: command(index, "left"),
          right: command(index, "right"),
        };
      }),
    },
    resource_evidence_reference: "metrics:employment-separation-perf-1",
    right_cleared: rightCleared,
    schema_version: "orgmetra.employment_separation.performance_fixture.v1",
    synthetic,
  };
}

export function acceptanceFixtureText(options) {
  return `${JSON.stringify(acceptanceFixture(options), null, 2)}\n`;
}

export function acceptanceFixtureBytes(options) {
  return Buffer.from(acceptanceFixtureText(options), "utf8");
}

export function acceptanceFixtureSha256(value) {
  return createHash("sha256").update(value).digest("hex");
}
