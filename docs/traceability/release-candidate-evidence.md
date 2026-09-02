# Release-candidate evidence traceability

## Scope and truth status

Protected-main truth at the branch point provides deterministic repository-source integrity, exact-head CI, security scanning, and a real PostgreSQL restore rehearsal. It does not yet provide a release-candidate evidence bundle that binds one exact Git revision to a reproducible source artifact, a software bill of materials, and structured provenance. This active PR adds that bounded evidence surface. It does **not** create a Git tag, GitHub Release, deployable container, signed attestation, SLSA level claim, certification claim, or permission to release.

The evidence builder reads immutable Git blobs from the exact checked-out commit rather than copying mutable working-tree bytes. It rejects a requested revision that differs from `HEAD`, rejects unsupported tree object modes, requires the exact **CPython 3.14.7** implementation/runtime used by the checked-in workflow, normalizes archive ownership/mode/time metadata, and builds twice in isolated temporary directories during CI. Source archive, SBOM, and provenance bytes must reproduce within the same declared builder mode.

## Build type v1

The build type identified by this document fragment has one external interface:

- `repository`: fixed to `https://github.com/ContextualWisdomLab/Orgmetra`;
- `sourceRevision`: the exact lowercase 40-character Git commit checked out by the workflow.

The checked-in builder is invoked as:

`python scripts/build-release-candidate-evidence.py --output-dir <isolated-directory> --source-sha <exact-head-sha>`

The builder emits exactly three candidate artifacts:

1. `orgmetra-source-<exact-head-sha>.tar.gz` — a deterministic GNU-tar/gzip representation of all tracked blobs in the commit, preserving only regular-file executable state and symbolic-link identity while normalizing uid/gid/names/mtime;
2. `orgmetra.cdx.json` — deterministic CycloneDX 1.7 JSON inventory for the source application, checked-in Python/npm package metadata, and declared dependency relationships discoverable from those package manifests;
3. `orgmetra.provenance.json` — an in-toto Statement v1 using the SLSA provenance v1 predicate type, whose subjects bind the source archive and SBOM SHA-256 digests and whose resolved source dependency binds the exact Git commit.

### Deterministic archive encoding

The source archive no longer delegates DEFLATE bytes to the host `zlib` implementation. `orgmetra-stored-gzip-v1` emits an RFC 1952 gzip member with normalized header metadata and RFC 1951 `BTYPE=00` stored blocks of at most 65,535 bytes, followed by the required CRC-32 and input-size trailer. This deliberately trades compression ratio for byte stability across hosted-image zlib refreshes. Standard gzip readers must decode the result back to the exact normalized GNU tar bytes.

The quality workflow still names `ubuntu-24.04` rather than the moving `ubuntu-latest` alias and pins checkout/setup actions by immutable commit SHA, but reproducible archive bytes do not rely on the host zlib implementation. CPython is pinned to the exact 3.14.7 patch release and the builder separately requires the implementation name `CPython`; another implementation reporting the same version string fails closed.

### Dependency identities

Only concrete Python pins and complete npm SemVer declarations may be promoted to package URLs. Python wildcard equality such as `==1.*`, npm partial versions such as `1.2`, ranges, and marker-bearing declarations remain declared requirements rather than fabricated concrete releases. Their component identities include a stable SHA-256-derived suffix over the **full declared requirement string** so distinct ranges or environment markers cannot collapse onto one `bom-ref`. The original declaration remains present as `orgmetra:declared-requirement` evidence.

PEP 621 `project.optional-dependencies` groups are part of the source declaration inventory. Each group is validated as a string array; its requirements retain their full declarations, are linked from the owning project component, and are represented with CycloneDX `scope=optional`. This makes checked-in test and feature extras visible without claiming they were installed or registry-resolved.

An exact Python dependency that names another checked-in project now merges with that existing local component instead of failing because local source components intentionally begin without dependency scope. The merged component retains `orgmetra:source:path`, adds the exact `orgmetra:declared-requirement`, receives the strongest observed dependency scope, and remains linked from both the source root and declaring project. This is declaration evidence only; it does not claim registry resolution.

Resolved PyPI component identity uses the same PEP 503 normalization for repeated declarations that is already used to build the package URL. Equivalent spellings such as `Foo_Bar` and `foo-bar` therefore share one exact pinned component and retain both original declaration strings, while genuinely different non-identity fields still fail closed.

An exact npm dependency that names a checked-in local package also merges into the existing local component. Component `type` is presentation/classification metadata rather than package identity during this merge, so a root `application` remains an application when a child package depends on it. The merged component keeps its source path, adds the exact declaration, receives the strongest scope, and retains the declaring-package edge.

Scoped npm package URLs follow the npm Package URL namespace rule: `@scope/name` is represented as separate namespace and package segments, for example `pkg:npm/%40scope/name@1.2.3`. The builder encodes the scope's `@` while preserving the namespace/name separator and uses the same helper for checked-in packages and declared dependencies.

### Builder identity

SLSA `runDetails.builder.id` must describe the actual execution mode rather than claiming GitHub Actions for every invocation. When `GITHUB_ACTIONS=true`, the unsigned candidate provenance identifies the checked-in GitHub Actions workflow. A local invocation instead uses the source-bound `#local-builder-v1` documentation identity and records `builderEnvironment=local`; local evidence therefore cannot silently claim the GitHub Actions builder identity. This remains workload-generated, unsigned provenance and is not trusted-control-plane attestation.

## Assurance boundary

The CycloneDX document is a source/declaration inventory, not a claim that every transitive runtime dependency has been resolved from a package registry or lockfile. Exact package pins receive package URLs only when the checked-in manifest supplies a concrete version; non-exact declarations remain explicit declared requirements rather than fabricated resolved versions. Lockfile-resolution and installed-dependency inventory remain separate release controls.

The SLSA-shaped provenance is intentionally **unsigned candidate provenance generated by the repository workload**. It improves deterministic correlation and downstream review but does not establish trusted-control-plane provenance, a signer identity, or any SLSA Build level. The in-toto envelope/signature layer and a release-platform attestation remain separate release controls. A production release process must independently enforce protected-head integration, qualifying review, applicable CI/security/coverage/recovery/package gates, artifact/SBOM/provenance digest verification, signing/attestation policy, rollback/recovery readiness, and release authorization before any version/tag/publication.

The exact-head quality workflow additionally builds one inspectable candidate bundle outside the source checkout and uploads it with the immutable `actions/upload-artifact` v4.6.2 commit. `if-no-files-found: error` prevents an empty success, and the seven-day retention window is review evidence only. The uploaded bundle does not become a signed release artifact or change the release-authority boundary.

## Executable evidence

| Requirement | Evidence | Expected result | Maturity |
|---|---|---|---|
| Exact source binding | workflow checkout proof plus builder `HEAD == --source-sha` guard | another commit cannot be labeled as the requested source | implemented_on_active_pr |
| Exact build-runtime binding | exact CPython 3.14.7 workflow pin, CPython implementation guard, and provenance assertions | another patch or Python implementation cannot emit evidence labeled as canonical | implemented_on_active_pr |
| Host-zlib independence | `orgmetra-stored-gzip-v1` regression plus source assertion excluding `gzip.compress` | standard gzip round-trip succeeds without host-zlib-generated evidence bytes | implemented_on_active_pr |
| Source archive reproducibility | two independent temporary-directory builds | source archive SHA-256 is byte-identical within one declared builder mode | implemented_on_active_pr |
| SBOM reproducibility | two independent temporary-directory builds | `orgmetra.cdx.json` SHA-256 is byte-identical | implemented_on_active_pr |
| Concrete-version discrimination | wildcard Python, partial npm, exact, prerelease, and build-metadata regressions | only concrete package versions receive package URLs | implemented_on_active_pr |
| Stable Python declaration identity | regression over distinct ranges and markers | non-exact requirements receive stable, distinct `bom-ref` values and dependency edges | implemented_on_active_pr |
| Canonical pinned Python identity | equivalent-name regression across separate manifests | PEP 503-equivalent exact pins merge into one component while retaining each declaration | implemented_on_active_pr |
| Local exact Python dependency linkage | checked-in project plus another project declaring its exact version | one local component retains source path, declaration, strongest scope, and declaring-project edge | implemented_on_active_pr |
| Local exact npm dependency linkage | root application plus child package declaring its exact version | the root keeps `type=application` while retaining source path, declaration, strongest scope, and child edge | implemented_on_active_pr |
| Canonical scoped npm identity | exact `@scope/name` dependency regression | package URL uses `%40scope/name` namespace/name segments rather than encoding the separator | implemented_on_active_pr |
| PEP 621 optional dependency inventory | synthetic optional-group contract plus repository manifests | optional requirements remain visible, correctly scoped, and linked to their project | implemented_on_active_pr |
| Stable final SBOM profile | `tests/release-candidate-evidence.test.mjs` | CycloneDX 1.7 identifiers, unique component references, product component, and declared components are present | implemented_on_active_pr |
| Provenance subject binding | same executable contract | source archive and SBOM subject digests match generated bytes | implemented_on_active_pr |
| Source-material binding | same executable contract | resolved Git dependency records the exact commit | implemented_on_active_pr |
| Honest builder identity | hosted/local execution regressions | local evidence cannot claim the GitHub Actions builder; builder mode is explicit | implemented_on_active_pr |
| Inspectable candidate retention | exact-head workflow contract plus immutable upload-artifact action | non-empty source/SBOM/provenance candidate bundle is downloadable for seven days | implemented_on_active_pr |
| Repository integrity | `npm run validate` in the dedicated workflow | protected foundation contracts remain unchanged and GREEN | implemented_on_active_pr |
| Read-only evidence generation | output goes to runner temporary storage plus final clean-checkout proof | tracked checkout remains unchanged | implemented_on_active_pr |

## Buyer and operator interpretation

A GREEN exact-head run proves that this repository revision can produce the three candidate evidence artifacts under the declared build type, exact CPython implementation/runtime, deterministic archive codec, and recorded builder mode, and that the same exact-head bundle can be inspected from the workflow artifact during its bounded retention window. It is useful for acquisition diligence, artifact-review automation, incident reconstruction, and future protected release automation. It does not mean Orgmetra has shipped, that a binary/container is reproducible, that the SBOM has registry-resolved every transitive dependency, or that the provenance is cryptographically authenticated.

Primary technical sources and APA 7 references are recorded in `docs/doctoring/release-candidate-evidence-references.md`.
