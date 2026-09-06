#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow_path="${repository_root}/.github/workflows/foundation-ci.yml"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"
compatibility_requirements_path="${repository_root}/.github/requirements/foundation-compatibility-test.txt"

expected_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-test.txt"
expected_compatibility_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-compatibility-test.txt"
expected_default_pr_target=$'  pull_request:\n    branches:\n      - develop\n'
expected_compatibility_matrix='        python-version: ["3.12", "3.13"]'
expected_package_discovery='for pyproject in packages/*/pyproject.toml; do'
expected_service_pythonpaths=(
  "services/job-analysis-api/src:packages/hris-kernel/src:packages/keyverse-adapter/src"
  "services/people-api/src:packages/hris-kernel/src:packages/keyverse-adapter/src"
)

if ! grep -Fq -- "${expected_install}" "${workflow_path}"; then
  printf 'Foundation CI must install only the hash-locked primary test toolchain.\n' >&2
  exit 1
fi

if ! grep -Fq -- "${expected_compatibility_install}" "${workflow_path}"; then
  printf 'Foundation CI must install the hash-locked compatibility toolchain.\n' >&2
  exit 1
fi

if grep -Eq -- 'python -m pip install .*packages/' "${workflow_path}"; then
  printf 'Foundation CI must not build/install repository-local packages into the checkout.\n' >&2
  exit 1
fi

if grep -Fq -- 'runs-on: ubuntu-latest' "${workflow_path}"; then
  printf 'Foundation CI must pin every GitHub-hosted job to ubuntu-24.04.\n' >&2
  exit 1
fi

if [[ "$(grep -Fc -- 'runs-on: ubuntu-24.04' "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation CI must pin both repository-quality and compatibility jobs to ubuntu-24.04.\n' >&2
  exit 1
fi

if ! grep -Fq -- "${expected_compatibility_matrix}" "${workflow_path}"; then
  printf 'Foundation CI must execute declared package compatibility on Python 3.12 and 3.13.\n' >&2
  exit 1
fi

if [[ "$(grep -Fc -- "${expected_package_discovery}" "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation CI must use package-neutral discovery in both primary and compatibility lanes.\n' >&2
  exit 1
fi

if grep -Eq -- 'packages/(interview-plan|selection-monitoring)' "${workflow_path}"; then
  printf 'Foundation CI must not encode package-name switchboards for compatibility adoption.\n' >&2
  exit 1
fi

if grep -Fq -- 'if ! python - "$pyproject"' "${workflow_path}"; then
  printf 'Foundation compatibility selection must not convert metadata/parser failures into unsupported-package skips.\n' >&2
  exit 1
fi

if ! grep -Fq -- 'compatibility_decision="$(' "${workflow_path}" ||
   ! grep -Fq -- 'from packaging.specifiers import InvalidSpecifier, SpecifierSet' "${workflow_path}" ||
   ! grep -Fq -- 'Unexpected compatibility decision for %s: %s' "${workflow_path}"; then
  printf 'Foundation compatibility selection must fail closed on invalid requires-python metadata.\n' >&2
  exit 1
fi

for expected_pythonpath in "${expected_service_pythonpaths[@]}"; do
  if ! grep -Fq -- "PYTHONPATH=${expected_pythonpath} COVERAGE_FILE=" "${workflow_path}"; then
    printf 'Foundation CI must preserve reviewed service source-tree execution: %s\n' "${expected_pythonpath}" >&2
    exit 1
  fi
done

if ! grep -Fq -- "${expected_default_pr_target}" "${workflow_path}"; then
  printf 'Foundation CI must run for pull requests targeting the repository default branch develop.\n' >&2
  exit 1
fi

mapfile -t pull_request_branches < <(
  awk '
    /^  pull_request:/ { in_pull_request=1; next }
    in_pull_request && /^  [[:alnum:]_-]+:/ { exit }
    in_pull_request && /^      - / {
      sub(/^      - /, "")
      print
    }
  ' "${workflow_path}"
)

if [[ "${#pull_request_branches[@]}" -eq 0 ]]; then
  printf 'Foundation CI must declare pull_request target branches.\n' >&2
  exit 1
fi

duplicate_pull_request_branches="$(
  printf '%s\n' "${pull_request_branches[@]}" | sort | uniq -d
)"
if [[ -n "${duplicate_pull_request_branches}" ]]; then
  printf 'Foundation CI pull_request branches must be unique: %s\n' "${duplicate_pull_request_branches}" >&2
  exit 1
fi

if [[ ! -f "${requirements_path}" ]]; then
  printf 'Hash-locked Foundation CI requirements are missing.\n' >&2
  exit 1
fi

mapfile -t package_lines < <(grep -Ev '^[[:space:]]*(#|$)' "${requirements_path}")
if [[ "${#package_lines[@]}" -ne 7 ]]; then
  printf 'Foundation CI requirements must contain the seven reviewed direct/runtime test packages.\n' >&2
  exit 1
fi

for package_line in "${package_lines[@]}"; do
  if [[ ! "${package_line}" =~ ^[A-Za-z0-9._-]+==[0-9][A-Za-z0-9._-]*[[:space:]]--hash=sha256:[0-9a-f]{64}$ ]]; then
    printf 'Unpinned or unhashed Foundation CI requirement: %s\n' "${package_line}" >&2
    exit 1
  fi
done

if [[ ! -f "${compatibility_requirements_path}" ]]; then
  printf 'Hash-locked Foundation compatibility requirements are missing.\n' >&2
  exit 1
fi

mapfile -t compatibility_package_lines < <(
  grep -Ev '^[[:space:]]*(#|$)' "${compatibility_requirements_path}"
)
if [[ "${#compatibility_package_lines[@]}" -ne 7 ]]; then
  printf 'Foundation compatibility requirements must contain the seven reviewed test packages.\n' >&2
  exit 1
fi

for package_line in "${compatibility_package_lines[@]}"; do
  if [[ ! "${package_line}" =~ ^[A-Za-z0-9._-]+==[0-9][A-Za-z0-9._-]*([[:space:]]--hash=sha256:[0-9a-f]{64})+$ ]]; then
    printf 'Unpinned or unhashed Foundation compatibility requirement: %s\n' "${package_line}" >&2
    exit 1
  fi
done

for package_name in coverage iniconfig packaging pluggy Pygments pytest pytest-cov; do
  if ! printf '%s\n' "${package_lines[@]}" | grep -Eq "^${package_name}=="; then
    printf 'Foundation CI requirement is missing: %s\n' "${package_name}" >&2
    exit 1
  fi
  if ! printf '%s\n' "${compatibility_package_lines[@]}" | grep -Eq "^${package_name}=="; then
    printf 'Foundation compatibility requirement is missing: %s\n' "${package_name}" >&2
    exit 1
  fi
done

coverage_compatibility_line="$(
  printf '%s\n' "${compatibility_package_lines[@]}" | grep '^coverage=='
)"
if [[ "$(grep -o -- '--hash=sha256:[0-9a-f]\{64\}' <<<"${coverage_compatibility_line}" | wc -l | tr -d ' ')" -ne 2 ]]; then
  printf 'Coverage compatibility requirement must bind reviewed CPython 3.12 and 3.13 wheels.\n' >&2
  exit 1
fi
