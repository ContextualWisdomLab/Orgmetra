# Foundation Python compatibility traceability

## Authority

- Repository: `ContextualWisdomLab/Orgmetra`
- Protected parent snapshot: `develop@eb9757f8649aaad026a9865508d9aad50c1a7a4f`
- Canonical repair issue: #258
- Maturity: `implemented_on_active_pr`

## Finding

Protected Foundation CI executes repository-owned Python quality on CPython 3.14, while several merged
packages declare `requires-python = ">=3.12"`. Structured Interview Plan #40 also carried real CPython
3.12/3.13 execution in its historical package-local workflow. Protected #161 correctly retired package-local
quality workflows, but adopting that deletion without replacement evidence would weaken the declared runtime
contract.

Three follow-up reviews found separate fail-open defects in the first compatibility implementation. Metadata
parser failures could be reclassified as unsupported-package skips; PEP 440 was evaluated against a fabricated
`major.minor.0` rather than the executed interpreter patch; and an owned `packages/*/pyproject.toml` could
escape package acceptance if either `src/` or `tests/` disappeared. Those paths now fail closed.

Exact-head Foundation run `34050838082` exposed a fourth defect in the implementation shape. Python 3.12 and
3.13 were introduced as a second matrix job, but protected repository policy intentionally constrains
Foundation to one job to avoid recreating the previous matrix-driven Actions admission pressure. The two
compatibility jobs themselves passed, while the canonical runner/queue contract failed before repository
validation. Compatibility evidence is therefore kept, but it executes sequentially inside the existing
`quality` job rather than widening the job graph.

Exact head `79e8757515673144b68687517360cf493e93ccb8` then produced a complete Foundation GREEN in run
`34053906336`: the one `Repository quality` job passed exact checkout, runner-image proof, Foundation validation,
dependency hygiene, primary package/service/PostgreSQL contracts, Python 3.12 compatibility, Python 3.13
compatibility, and clean-checkout proof.

A fifth review found a provenance gap despite that GREEN. The compatibility requirement file was hash-locked at
the package line level, but the file itself was not part of the canonical Foundation manifest inventory. A
reviewed dependency set could therefore change without changing the manifest unless another tracked artifact
bound it. The active successor now makes that binding explicit: the manifest-sealed Foundation workflow verifies
SHA-256 `cebb36181e8ac995a36d73a02a45094a204ff5adb3cbcdc0c9eccff309ac6aab` for
`.github/requirements/foundation-compatibility-test.txt` before either compatibility runtime can install it.
The workflow itself is resealed in `manifest.json`, so the dependency input is transitively integrity-bound
without adding a second quality owner or mutable external source.

A package-local workflow is not restored. The capability remains owned by
`.github/workflows/foundation-ci.yml`.

## Decision

Foundation keeps one `quality` job on pinned `ubuntu-24.04`. That job runs the primary CPython 3.14 package,
service, and PostgreSQL contracts, proves the reviewed compatibility-toolchain file digest, then switches to
CPython 3.12 and CPython 3.13 in sequence with `actions/setup-python`. Each compatibility runtime installs the
same reviewed hash-locked compatibility toolchain and executes every package whose `project.requires-python`
includes the actual interpreter patch. No compatibility matrix or second Foundation job is permitted.

Primary and compatibility package execution discover `packages/*/pyproject.toml` rather than naming packages
in workflow logic. For each compatibility runtime, Foundation reads `project.requires-python` with `tomllib`
and `packaging.specifiers.SpecifierSet`, evaluates it against
`sys.version_info.major.minor.micro`, and permits a skip only when a syntactically valid constraint excludes
that exact executed release. Missing, blank, non-string, malformed TOML, invalid specifiers, or parser failures
terminate the compatibility execution. Every selected package is compiled and runs its own pytest
configuration, preserving its exact statement and branch coverage gate.

The repository-quality hygiene contract independently enumerates every `packages/*/pyproject.toml` and
requires both `src/` and `tests/`. Its self-regression constructs missing-`src` and missing-`tests` fixtures and
requires both to fail closed. Non-Python directories without a `pyproject.toml` remain outside this contract.

The primary CPython 3.14 toolchain remains bound by `.github/requirements/foundation-test.txt`. CPython
3.12/3.13 use `.github/requirements/foundation-compatibility-test.txt`, installed with
`--require-hashes --no-deps --only-binary=:all:` and reviewed wheel hashes for both compatibility runtimes. The
compatibility file's complete bytes are additionally pinned by the manifest-sealed Foundation workflow before
installation.

## Invariants

- `.github/workflows/foundation-ci.yml` remains the only repository quality owner.
- Foundation expands to exactly one repository-owned job; compatibility must not add a matrix or second job.
- The Foundation job uses `ubuntu-24.04`; `ubuntu-latest` remains rejected by executable regression.
- CPython 3.12 and 3.13 compatibility executes sequentially after the primary CPython 3.14 quality contracts.
- The compatibility requirement file must match the reviewed SHA-256 before either compatibility install.
- Compatibility discovery is package-neutral and contains no Interview Plan or Selection Monitoring switch.
- Every discovered owned Python package has both `src/` and `tests/`; incomplete layout is a Foundation
  failure rather than an accepted skip.
- Invalid or missing `project.requires-python` metadata fails closed; only a valid constraint excluding the
  actual executed interpreter patch may skip a package.
- Patch-sensitive PEP 440 constraints are evaluated against the executed release, never a fabricated `.0`.
- Each compatibility runtime fails if no owned package actually declares that runtime supported.
- Repository-local packages are not installed into the checkout as an implicit dependency workaround.
- Package-local quality workflows retired by protected #161 remain retired.

## Scope boundary

This change proves declared compatibility for Python packages under `packages/`. The two HTTP services
currently declare Python 3.11 support but remain a separate #260 service-runtime contract. No Python 3.11
service-compatibility claim is made by #258 or #40.

## Adoption

After this capability is integrated on protected `develop`, #40 can discard
`.github/workflows/interview-plan-quality.yml`, retain its `requires-python = ">=3.12"` declaration and
package tests, and receive Python 3.12/3.13/3.14 evidence through Foundation without adding a package name to
shared workflow logic. #42 should likewise adopt the protected generic package execution rather than copying
its mutable shared-dispatcher implementation.
