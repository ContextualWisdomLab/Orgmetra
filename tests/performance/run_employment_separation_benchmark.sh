#!/usr/bin/env bash
set -euo pipefail

readonly PINNED_K6_VERSION="2.2.0"
readonly WORKLOAD="tests/performance/employment_separation_buyer_path.js"

k6_bin="${K6_BIN:-k6}"
if ! command -v "${k6_bin}" >/dev/null 2>&1; then
  printf 'pinned k6 runner is unavailable: %s\n' "${k6_bin}" >&2
  exit 1
fi

version_line="$(${k6_bin} version 2>&1 | head -n 1)"
version_token="$(printf '%s\n' "${version_line}" | awk '{print $2}')"
if [[ "${version_token}" != "v${PINNED_K6_VERSION}" ]]; then
  printf 'commercial Employment separation performance runs require k6 v%s; observed: %s\n' \
    "${PINNED_K6_VERSION}" "${version_line}" >&2
  exit 1
fi

export ORGMETRA_PERFORMANCE_K6_VERSION="${PINNED_K6_VERSION}"
exec "${k6_bin}" run "${WORKLOAD}" "$@"
