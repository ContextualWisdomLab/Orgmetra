import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import {
  PINNED_K6_IMAGE,
  PINNED_K6_IMAGE_DIGEST,
  PINNED_K6_RUNNER_IDENTITY,
  PINNED_K6_VERSION,
  requirePinnedK6Runtime,
  requirePinnedK6Version,
} from "./employment_separation_k6_runtime_contract.mjs";

function validRuntime() {
  return {
    version: PINNED_K6_VERSION,
    image: PINNED_K6_IMAGE,
    imageDigest: PINNED_K6_IMAGE_DIGEST,
    runnerIdentity: PINNED_K6_RUNNER_IDENTITY,
  };
}

test("accepts only the repository-pinned upstream k6 OCI image", () => {
  assert.equal(PINNED_K6_VERSION, "2.2.0");
  assert.equal(requirePinnedK6Version("2.2.0"), "2.2.0");
  assert.deepEqual(requirePinnedK6Runtime(validRuntime()), {
    version: PINNED_K6_VERSION,
    image: PINNED_K6_IMAGE,
    image_digest: PINNED_K6_IMAGE_DIGEST,
    runner_identity: PINNED_K6_RUNNER_IDENTITY,
  });
});

test("rejects substituted versions, images, digests, and runner identities", () => {
  for (const value of ["", "2.1.0", "2.2.1", "2.3.0", "v2.2.0", "2.2.0-dev"]) {
    assert.throws(() => requirePinnedK6Version(value), /require k6 2\.2\.0/);
  }
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), image: "example.invalid/k6" }), /require ghcr\.io\/grafana\/k6/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), imageDigest: `sha256:${"0".repeat(64)}` }), /OCI image digest/);
  assert.throws(() => requirePinnedK6Runtime({ ...validRuntime(), runnerIdentity: "ghcr.io/grafana/k6@sha256:substitute" }), /runner identity/);
});

test("canonical benchmark runner does not accept ungoverned k6 CLI overrides", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.doesNotMatch(
    runner,
    /"\$@"/,
    "arbitrary k6 CLI flags can override version-controlled script options and __ENV inputs",
  );
  assert.match(
    runner,
    /"\$\{PINNED_K6_RUNNER_IDENTITY\}" run "\$\{WORKLOAD\}"\s*$/m,
    "commercial measurement must end at the version-controlled workload without caller-supplied k6 flags",
  );
});

test("canonical benchmark runner does not forward caller-controlled load-model environment", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  for (const name of [
    "ORGMETRA_PERFORMANCE_TARGET_RPS",
    "ORGMETRA_PERFORMANCE_DURATION_SECONDS",
    "ORGMETRA_PERFORMANCE_PREALLOCATED_VUS",
    "ORGMETRA_PERFORMANCE_MAX_VUS",
  ]) {
    assert.doesNotMatch(runner, new RegExp(`--env ${name}(?:\\s|$)`), `${name} must be version-controlled by the workload`);
  }
});

test("canonical benchmark runner binds the mounted workload to an immutable exact-candidate image", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" rev-parse --verify HEAD/,
    "the source repository must be checked against an exact HEAD before materialization",
  );
  assert.match(
    runner,
    /repository_head.*ORGMETRA_PERFORMANCE_TARGET_SHA|ORGMETRA_PERFORMANCE_TARGET_SHA.*repository_head/s,
    "the exact source checkout must match the measured candidate SHA",
  );
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" status --porcelain=v1 --untracked-files=all/,
    "commercial evidence must reject modified, staged, or untracked source bytes",
  );
  assert.match(
    runner,
    /git -C "\$\{repo_root\}" archive --format=tar "\$\{target_sha\}"[\s\S]*podman import/,
    "the executed workload must be imported from the verified immutable candidate commit",
  );
  assert.doesNotMatch(
    runner,
    /--volume "\$\{repo_root\}:\/workspace:ro"/,
    "the live host working tree must never be mounted as the executable workload",
  );
  assert.match(
    runner,
    /--mount "type=image,source=\$\{workload_image_id\},destination=\/workspace"/,
    "Podman must mount only the imported candidate image at /workspace",
  );
  assert.match(
    runner,
    /podman image rm --force "\$\{workload_image_id\}"/,
    "the ephemeral candidate image must be removed after the run",
  );
});

test("canonical benchmark runner maps host evidence ownership to the pinned non-root k6 user", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.match(runner, /readonly PINNED_K6_CONTAINER_UID="12345"/);
  assert.match(runner, /readonly PINNED_K6_CONTAINER_GID="12345"/);
  assert.match(
    runner,
    /podman image inspect --format '\{\{\.Config\.User\}\}' "\$\{PINNED_K6_RUNNER_IDENTITY\}"/,
    "the pinned OCI image's configured non-root user must be verified before measurement",
  );
  assert.match(
    runner,
    /--userns="keep-id:uid=\$\{PINNED_K6_CONTAINER_UID\},gid=\$\{PINNED_K6_CONTAINER_GID\}"/,
    "the invoking host owner must map to k6 UID/GID so private fixture and staging paths remain usable without world-writable permissions",
  );
});

test("canonical benchmark runner cannot publish stale or failed-run summary evidence", () => {
  const runner = readFileSync(new URL("./run_employment_separation_benchmark.sh", import.meta.url), "utf8");
  assert.match(
    runner,
    /summary_target="\$\{summary_dir\}\/\$\{summary_name\}"/,
    "the requested result path must be treated as a final publication target",
  );
  assert.match(
    runner,
    /if \[\[ -e "\$\{summary_target\}" \|\| -L "\$\{summary_target\}" \]\]/,
    "a pre-existing result artifact must fail closed instead of surviving a failed rerun",
  );
  assert.match(
    runner,
    /mktemp -d .*orgmetra-employment-separation-performance/,
    "k6 must write into a private per-run staging directory",
  );
  assert.doesNotMatch(
    runner,
    /--volume "\$\{summary_dir\}:\/output:rw"/,
    "k6 must not write directly into the caller-visible result directory",
  );
  assert.match(
    runner,
    /\[\[ ! -f "\$\{summary_run_file\}" \|\| -L "\$\{summary_run_file\}" \|\| ! -s "\$\{summary_run_file\}" \]\]/,
    "the staged result must be a non-empty regular file",
  );
  assert.match(
    runner,
    /summary_source_identity=.*stat --printf='%d:%i:%s'/,
    "publication must bind the validated source device, inode, and size before linking",
  );
  assert.match(
    runner,
    /summary_source_digest=.*sha256sum/,
    "publication must bind the exact validated source bytes before linking",
  );
  assert.match(
    runner,
    /ln "\$\{summary_run_file\}" "\$\{summary_target\}"/,
    "publication must use a no-clobber atomic link so a concurrent stale artifact cannot win",
  );
  assert.match(
    runner,
    /summary_target_identity=.*stat --printf='%d:%i:%s'/,
    "the published link must be re-identified after link creation",
  );
  assert.match(
    runner,
    /summary_target_digest=.*sha256sum/,
    "the published link bytes must be re-hashed after link creation",
  );
  assert.match(
    runner,
    /summary_source_identity[\s\S]*summary_source_identity_after[\s\S]*summary_target_identity[\s\S]*summary_source_digest[\s\S]*summary_source_digest_after[\s\S]*summary_target_digest/,
    "source identity and bytes must remain unchanged across publication and equal the published artifact",
  );
  assert.match(
    runner,
    /rm -f -- "\$\{summary_target\}"/,
    "a publication-integrity mismatch must remove the untrusted caller-visible artifact before failing",
  );
});

test("canonical benchmark runner rejects a staged-path replacement during publication", () => {
  const repoRoot = fileURLToPath(new URL("../..", import.meta.url));
  const runnerPath = fileURLToPath(new URL("./run_employment_separation_benchmark.sh", import.meta.url));
  const temporaryRoot = mkdtempSync(join(tmpdir(), "orgmetra-summary-publication-race-"));
  try {
    const fakeBin = join(temporaryRoot, "bin");
    mkdirSync(fakeBin);
    const podmanPath = join(fakeBin, "podman");
    writeFileSync(
      podmanPath,
      `#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "image" && "$2" == "exists" ]]; then exit 0; fi
if [[ "$1" == "image" && "$2" == "inspect" ]]; then printf '12345\\n'; exit 0; fi
if [[ "$1" == "image" && "$2" == "rm" ]]; then exit 0; fi
if [[ "$1" == "import" ]]; then cat >/dev/null; printf 'sha256:fake-workload\\n'; exit 0; fi
if [[ "$1" == "run" ]]; then
  if [[ "\${!#}" == "version" ]]; then printf 'k6 v2.2.0\\n'; exit 0; fi
  output_dir=''
  summary_name=''
  args=("$@")
  for ((i=0; i<\${#args[@]}; i++)); do
    if [[ "\${args[$i]}" == "--volume" ]]; then
      value="\${args[$((i+1))]}"
      if [[ "$value" == *":/output:rw" ]]; then output_dir="\${value%:/output:rw}"; fi
    fi
    if [[ "\${args[$i]}" == "--env" ]]; then
      value="\${args[$((i+1))]}"
      if [[ "$value" == ORGMETRA_PERFORMANCE_SUMMARY_FILE=/output/* ]]; then
        summary_name="\${value#ORGMETRA_PERFORMANCE_SUMMARY_FILE=/output/}"
      fi
    fi
  done
  [[ -n "$output_dir" && -n "$summary_name" ]]
  printf '{"schema_version":"orgmetra.race_probe.original"}\\n' > "$output_dir/$summary_name"
  exit 0
fi
exit 99
`,
      { mode: 0o700 },
    );
    chmodSync(podmanPath, 0o700);

    const lnPath = join(fakeBin, "ln");
    writeFileSync(
      lnPath,
      `#!/usr/bin/env bash
set -euo pipefail
printf '{"schema_version":"orgmetra.race_probe.replaced"}\\n' > "$1"
exec /bin/ln "$@"
`,
      { mode: 0o700 },
    );
    chmodSync(lnPath, 0o700);

    const fixturePath = join(temporaryRoot, "fixture.json");
    const summaryPath = join(temporaryRoot, "result.json");
    writeFileSync(fixturePath, "{}\n", { mode: 0o600 });

    const head = spawnSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], { encoding: "utf8" });
    assert.equal(head.status, 0, head.stderr);
    const targetSha = head.stdout.trim();
    const result = spawnSync("bash", [runnerPath], {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        PATH: `${fakeBin}:${process.env.PATH ?? ""}`,
        ORGMETRA_PERFORMANCE_BASE_URL: "http://127.0.0.1:18080",
        ORGMETRA_PERFORMANCE_BEARER_TOKEN: "test-only-token",
        ORGMETRA_PERFORMANCE_TARGET_SHA: targetSha,
        ORGMETRA_PERFORMANCE_PROFILE: "first_commit",
        ORGMETRA_PERFORMANCE_DATA_FILE: fixturePath,
        ORGMETRA_PERFORMANCE_SUMMARY_FILE: summaryPath,
      },
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /summary changed during publication/);
    assert.equal(existsSync(summaryPath), false, "a replaced staged artifact must never remain published");
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

test("canonical benchmark runner rejects CLI overrides before any Podman dependency is needed", () => {
  const runnerPath = fileURLToPath(new URL("./run_employment_separation_benchmark.sh", import.meta.url));
  const result = spawnSync("bash", [runnerPath, "--duration", "1s"], {
    encoding: "utf8",
    env: { PATH: process.env.PATH ?? "" },
  });
  assert.equal(result.status, 64);
  assert.match(result.stderr, /does not accept caller-supplied k6 CLI options/);
});
