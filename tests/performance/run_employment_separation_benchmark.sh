#!/usr/bin/env bash
set -euo pipefail

readonly PINNED_K6_VERSION="2.2.0"
readonly PINNED_K6_IMAGE="ghcr.io/grafana/k6"
readonly PINNED_K6_IMAGE_DIGEST="sha256:9bd01d6941fca969cb61bb57d2da5ee9b385fe2aa8881df3798c196564d6ace6"
readonly PINNED_K6_RUNNER_IDENTITY="${PINNED_K6_IMAGE}@${PINNED_K6_IMAGE_DIGEST}"
readonly PINNED_K6_CONTAINER_UID="12345"
readonly PINNED_K6_CONTAINER_GID="12345"
readonly MAXIMUM_FIXTURE_ARTIFACT_BYTES="8388608"
readonly WORKLOAD="/workspace/tests/performance/employment_separation_buyer_path.js"

if (( $# != 0 )); then
  printf 'commercial Employment separation benchmark does not accept caller-supplied k6 CLI options\n' >&2
  exit 64
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
target_sha="${ORGMETRA_PERFORMANCE_TARGET_SHA:-}"
if [[ ! "${target_sha}" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'ORGMETRA_PERFORMANCE_TARGET_SHA must be the exact lowercase 40-character candidate SHA\n' >&2
  exit 1
fi
repository_head="$(git -C "${repo_root}" rev-parse --verify HEAD)"
if [[ "${repository_head}" != "${ORGMETRA_PERFORMANCE_TARGET_SHA}" ]]; then
  printf 'benchmark checkout HEAD must equal ORGMETRA_PERFORMANCE_TARGET_SHA; head=%s target=%s\n' "${repository_head}" "${ORGMETRA_PERFORMANCE_TARGET_SHA}" >&2
  exit 1
fi
repository_status="$(git -C "${repo_root}" status --porcelain=v1 --untracked-files=all)"
if [[ -n "${repository_status}" ]]; then
  printf 'commercial performance evidence requires an exact clean checkout; modified, staged, or untracked files are present\n' >&2
  exit 1
fi

fixture_path="${ORGMETRA_PERFORMANCE_DATA_FILE:-}"
summary_path="${ORGMETRA_PERFORMANCE_SUMMARY_FILE:-}"
if [[ -z "${fixture_path}" || ! -f "${fixture_path}" ]]; then
  printf 'ORGMETRA_PERFORMANCE_DATA_FILE must point to the right-cleared fixture\n' >&2
  exit 1
fi
fixture_path="$(realpath "${fixture_path}")"
fixture_bytes="$(stat --printf='%s' -- "${fixture_path}")"
if [[ ! "${fixture_bytes}" =~ ^[0-9]+$ ]] || (( fixture_bytes > MAXIMUM_FIXTURE_ARTIFACT_BYTES )); then
  printf 'performance fixture must not exceed %s bytes\n' "${MAXIMUM_FIXTURE_ARTIFACT_BYTES}" >&2
  exit 1
fi

if ! command -v podman >/dev/null 2>&1; then
  printf 'podman is required for the pinned commercial k6 runner\n' >&2
  exit 1
fi
if ! podman image exists "${PINNED_K6_RUNNER_IDENTITY}"; then
  printf 'preload the exact pinned k6 image before measurement: %s\n' "${PINNED_K6_RUNNER_IDENTITY}" >&2
  exit 1
fi
image_user="$(podman image inspect --format '{{.Config.User}}' "${PINNED_K6_RUNNER_IDENTITY}")"
if [[ "${image_user}" != "${PINNED_K6_CONTAINER_UID}" ]]; then
  printf 'pinned k6 image must declare container UID %s; observed: %s\n' "${PINNED_K6_CONTAINER_UID}" "${image_user}" >&2
  exit 1
fi
version_line="$(podman run --rm --pull=never "${PINNED_K6_RUNNER_IDENTITY}" version 2>&1 | head -n 1)"
version_token="$(printf '%s\n' "${version_line}" | awk '{print $2}')"
if [[ "${version_token}" != "v${PINNED_K6_VERSION}" ]]; then
  printf 'pinned k6 image must report v%s; observed: %s\n' "${PINNED_K6_VERSION}" "${version_line}" >&2
  exit 1
fi

workload_image_id=""
summary_run_dir=""
cleanup() {
  if [[ -n "${workload_image_id}" ]]; then
    podman image rm --force "${workload_image_id}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${summary_run_dir}" ]]; then
    rm -rf -- "${summary_run_dir}"
  fi
}
trap cleanup EXIT
workload_image_id="$(
  git -C "${repo_root}" archive --format=tar "${target_sha}" \
    | podman import --quiet --message "Orgmetra Employment separation benchmark ${target_sha}" -
)"
if [[ -z "${workload_image_id}" ]] || ! podman image exists "${workload_image_id}"; then
  printf 'failed to materialize immutable benchmark workload image for %s\n' "${target_sha}" >&2
  exit 1
fi

if [[ -z "${summary_path}" ]]; then
  printf 'ORGMETRA_PERFORMANCE_SUMMARY_FILE is required\n' >&2
  exit 1
fi
summary_dir="$(realpath -m "$(dirname "${summary_path}")")"
summary_name="$(basename "${summary_path}")"
mkdir -p "${summary_dir}"
summary_target="${summary_dir}/${summary_name}"
if [[ -e "${summary_target}" || -L "${summary_target}" ]]; then
  printf 'ORGMETRA_PERFORMANCE_SUMMARY_FILE must not already exist; refusing stale-result reuse: %s\n' "${summary_target}" >&2
  exit 1
fi
summary_run_dir="$(mktemp -d "${summary_dir}/.orgmetra-employment-separation-performance.XXXXXX")"
summary_run_file="${summary_run_dir}/${summary_name}"

export ORGMETRA_PERFORMANCE_K6_VERSION="${PINNED_K6_VERSION}"
export ORGMETRA_PERFORMANCE_K6_IMAGE="${PINNED_K6_IMAGE}"
export ORGMETRA_PERFORMANCE_K6_IMAGE_DIGEST="${PINNED_K6_IMAGE_DIGEST}"
export ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY="${PINNED_K6_RUNNER_IDENTITY}"

podman run --rm --pull=never --network=host --read-only \
  --user="${PINNED_K6_CONTAINER_UID}:${PINNED_K6_CONTAINER_GID}" \
  --userns="keep-id:uid=${PINNED_K6_CONTAINER_UID},gid=${PINNED_K6_CONTAINER_GID}" \
  --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=256 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --mount "type=image,source=${workload_image_id},destination=/workspace" \
  --volume "${fixture_path}:/evidence/fixture.json:ro" \
  --volume "${summary_run_dir}:/output:rw" \
  --workdir /workspace \
  --env ORGMETRA_PERFORMANCE_BASE_URL \
  --env ORGMETRA_PERFORMANCE_BEARER_TOKEN \
  --env ORGMETRA_PERFORMANCE_TARGET_SHA \
  --env ORGMETRA_PERFORMANCE_PROFILE \
  --env ORGMETRA_PERFORMANCE_K6_VERSION \
  --env ORGMETRA_PERFORMANCE_K6_IMAGE \
  --env ORGMETRA_PERFORMANCE_K6_IMAGE_DIGEST \
  --env ORGMETRA_PERFORMANCE_K6_RUNNER_IDENTITY \
  --env ORGMETRA_PERFORMANCE_DATA_FILE=/evidence/fixture.json \
  --env "ORGMETRA_PERFORMANCE_SUMMARY_FILE=/output/${summary_name}" \
  "${PINNED_K6_RUNNER_IDENTITY}" run "${WORKLOAD}"

if [[ ! -f "${summary_run_file}" || -L "${summary_run_file}" || ! -s "${summary_run_file}" ]]; then
  printf 'successful k6 execution did not produce one non-empty regular summary artifact\n' >&2
  exit 1
fi
summary_source_identity="$(stat --printf='%d:%i:%s' -- "${summary_run_file}")"
summary_source_digest="$(sha256sum -- "${summary_run_file}" | awk '{print $1}')"
if ! ln "${summary_run_file}" "${summary_target}"; then
  printf 'failed to publish benchmark summary without clobbering an existing artifact: %s\n' "${summary_target}" >&2
  exit 1
fi
summary_source_identity_after="$(stat --printf='%d:%i:%s' -- "${summary_run_file}" 2>/dev/null || true)"
summary_source_digest_after="$(sha256sum -- "${summary_run_file}" 2>/dev/null | awk '{print $1}' || true)"
summary_target_identity="$(stat --printf='%d:%i:%s' -- "${summary_target}" 2>/dev/null || true)"
summary_target_digest="$(sha256sum -- "${summary_target}" 2>/dev/null | awk '{print $1}' || true)"
if [[ -z "${summary_source_identity_after}" || -z "${summary_source_digest_after}" || -z "${summary_target_identity}" || -z "${summary_target_digest}" \
  || "${summary_source_identity}" != "${summary_source_identity_after}" \
  || "${summary_source_identity}" != "${summary_target_identity}" \
  || "${summary_source_digest}" != "${summary_source_digest_after}" \
  || "${summary_source_digest}" != "${summary_target_digest}" ]]; then
  rm -f -- "${summary_target}"
  printf 'benchmark summary changed during publication; refusing unbound result evidence\n' >&2
  exit 1
fi

# This digest is structural evidence only. The caller-visible pathname and any
# value a caller can copy from stdout remain under the same authority. Commercial
# acceptance stays fail closed until the organization-owned authenticated
# attestation boundary tracked by ContextualWisdomLab/.github#2162 binds these
# exact result bytes independently.
printf 'ORGMETRA_PERFORMANCE_RESULT_SHA256=%s\n' "${summary_source_digest}"
