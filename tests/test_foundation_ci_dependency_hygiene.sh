#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workflow_path="${repository_root}/.github/workflows/foundation-ci.yml"
requirements_path="${repository_root}/.github/requirements/foundation-test.txt"
compatibility_requirements_path="${repository_root}/.github/requirements/foundation-compatibility-test.txt"

expected_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-test.txt"
expected_compatibility_install="python -m pip install --require-hashes --no-deps --only-binary=:all: -r .github/requirements/foundation-compatibility-test.txt"
expected_default_pr_target=$'  pull_request:\n    branches:\n      - develop\n'
expected_package_discovery='for pyproject in packages/*/pyproject.toml; do'
expected_service_pythonpaths=(
  "services/job-analysis-api/src:packages/hris-kernel/src:packages/keyverse-adapter/src"
  "services/people-api/src:packages/hris-kernel/src:packages/keyverse-adapter/src"
)

validate_owned_package_layout() {
  local root="$1"
  local pyproject
  local package_dir
  local discovered=0

  for pyproject in "${root}"/packages/*/pyproject.toml; do
    [[ -f "${pyproject}" ]] || continue
    discovered=$((discovered + 1))
    package_dir="${pyproject%/pyproject.toml}"
    if [[ ! -d "${package_dir}/src" || ! -d "${package_dir}/tests" ]]; then
      printf 'Owned Python package must provide both src and tests directories: %s\n' "${package_dir}" >&2
      return 1
    fi
  done

  if [[ "${discovered}" -eq 0 ]]; then
    printf 'Foundation CI package discovery found no owned Python packages.\n' >&2
    return 1
  fi
}

validate_owned_package_layout "${repository_root}"

layout_fixture_root="$(mktemp -d)"
trap 'rm -rf "${layout_fixture_root}"' EXIT
for missing_directory in src tests; do
  fixture_package="${layout_fixture_root}/packages/missing-${missing_directory}"
  mkdir -p "${fixture_package}/src" "${fixture_package}/tests"
  rm -rf "${fixture_package}/${missing_directory}"
  cat >"${fixture_package}/pyproject.toml" <<'EOF'
[project]
name = "orgmetra-foundation-layout-fixture"
version = "0.0.0"
requires-python = ">=3.12"
EOF
  if validate_owned_package_layout "${layout_fixture_root}" >/dev/null 2>&1; then
    printf 'Foundation package discovery must fail closed when an owned package omits %s.\n' "${missing_directory}" >&2
    exit 1
  fi
  rm -rf "${fixture_package}"
done
rm -rf "${layout_fixture_root}"
trap - EXIT

if ! grep -Fq -- "${expected_install}" "${workflow_path}"; then
  printf 'Foundation CI must install only the hash-locked primary test toolchain.\n' >&2
  exit 1
fi

if [[ "$(grep -Fc -- "${expected_compatibility_install}" "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation CI must install the hash-locked compatibility toolchain once for each declared compatibility runtime.\n' >&2
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

if [[ "$(grep -Fc -- 'runs-on: ubuntu-24.04' "${workflow_path}")" -ne 1 ]]; then
  printf 'Foundation CI must preserve one repository-owned job on ubuntu-24.04.\n' >&2
  exit 1
fi

if grep -Fq -- 'matrix:' "${workflow_path}" || grep -Fq -- 'python-compatibility:' "${workflow_path}"; then
  printf 'Foundation compatibility must not recreate matrix-driven or second-job admission pressure.\n' >&2
  exit 1
fi

for python_minor in 3.12 3.13; do
  if [[ "$(grep -Fc -- "python-version: \"${python_minor}\"" "${workflow_path}")" -ne 1 ]]; then
    printf 'Foundation CI must set up Python %s exactly once for sequential compatibility evidence.\n' "${python_minor}" >&2
    exit 1
  fi
  if [[ "$(grep -Fc -- "ORGMETRA_PYTHON_MINOR: \"${python_minor}\"" "${workflow_path}")" -ne 1 ]]; then
    printf 'Foundation CI must bind compatibility execution to Python %s.\n' "${python_minor}" >&2
    exit 1
  fi
done

if [[ "$(grep -Fc -- "${expected_package_discovery}" "${workflow_path}")" -ne 3 ]]; then
  printf 'Foundation CI must use package-neutral discovery in primary, Python 3.12, and Python 3.13 execution.\n' >&2
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

if [[ "$(grep -Fc -- 'compatibility_decision="$(' "${workflow_path}")" -ne 2 ]] ||
   [[ "$(grep -Fc -- 'from packaging.specifiers import InvalidSpecifier, SpecifierSet' "${workflow_path}")" -ne 2 ]] ||
   [[ "$(grep -Fc -- 'Unexpected compatibility decision for %s: %s' "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation compatibility selection must fail closed in both sequential compatibility executions.\n' >&2
  exit 1
fi

expected_exact_runtime='runtime = Version(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
if [[ "$(grep -Fc -- "${expected_exact_runtime}" "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation compatibility selection must evaluate both runtimes against the exact executed interpreter patch.\n' >&2
  exit 1
fi

if grep -Fq -- 'runtime = Version(f"{sys.version_info.major}.{sys.version_info.minor}.0")' "${workflow_path}"; then
  printf 'Foundation compatibility selection must not fabricate a .0 patch for requires-python checks.\n' >&2
  exit 1
fi

if [[ "$(grep -Fc -- 'No owned package declared Python %s support; compatibility evidence would be vacuous.' "${workflow_path}")" -ne 2 ]]; then
  printf 'Foundation compatibility must fail non-vacuously for both sequential runtimes.\n' >&2
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
