import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = new URL('../', import.meta.url);

/** Import the actual config in a bounded child with an isolated port/CI setting. */
function importBrowserConfig({ port, ci } = {}) {
  const env = { ...process.env };
  delete env.ORGMETRA_WORKSPACE_PORT;
  delete env.CI;
  if (port !== undefined) env.ORGMETRA_WORKSPACE_PORT = port;
  if (ci !== undefined) env.CI = ci;
  const result = spawnSync(process.execPath, ['--input-type=module', '-e',
    "import config from './playwright.config.mjs'; console.log(JSON.stringify(config));"], {
    cwd: fileURLToPath(root), env, encoding: 'utf8', timeout: 15_000,
  });
  assert.equal(result.error, undefined, 'config import must finish within its bound');
  return result;
}

test('browser acceptance always owns its fixture instead of reusing a foreign HTTP server', () => {
  for (const ci of [undefined, 'true', '']) {
    const result = importBrowserConfig({ ci });
    assert.equal(result.status, 0, result.stderr);
    const config = JSON.parse(result.stdout);
    assert.equal(config.webServer.reuseExistingServer, false);
    assert.equal(config.use.baseURL, 'http://127.0.0.1:4173');
    assert.equal(config.webServer.url, 'http://127.0.0.1:4173/apps/hr-workspace/index.html');
    assert.equal(config.webServer.command, 'python3 -m http.server 4173 --bind 127.0.0.1');
    assert.equal(config.timeout, 15_000);
    assert.equal(config.expect.timeout, 5_000);
    assert.equal(config.use.trace, 'retain-on-failure');
    assert.equal(config.use.screenshot, 'only-on-failure');
    assert.equal(config.use.video, 'retain-on-failure');
  }
});

test('browser fixture uses a configured canonical TCP port consistently', () => {
  for (const port of ['1', '43127', '65535']) {
    const result = importBrowserConfig({ port });
    assert.equal(result.status, 0, result.stderr);
    const config = JSON.parse(result.stdout);
    assert.equal(config.use.baseURL, `http://127.0.0.1:${port}`);
    assert.equal(config.webServer.url, `http://127.0.0.1:${port}/apps/hr-workspace/index.html`);
    assert.equal(config.webServer.command, `python3 -m http.server ${port} --bind 127.0.0.1`);
    assert.equal(config.webServer.reuseExistingServer, false);
  }
});

test('browser fixture rejects invalid port grammar and bounds before returning a server config', () => {
  const invalidPorts = ['', '0', '65536', '-1', '+4173', '04173', ' 4173', '4173 ',
    '4173\n', '4.173', '4e3', '0x104d', 'NaN', 'Infinity', '999999999999999999999', '4173; echo unsafe'];
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', `
    const results = [];
    for (const [index, port] of JSON.parse(process.argv[1]).entries()) {
      process.env.ORGMETRA_WORKSPACE_PORT = port;
      try {
        await import('./playwright.config.mjs?invalid=' + index);
        results.push({ rejected: false });
      } catch (error) {
        results.push({ rejected: true, message: error.message });
      }
    }
    console.log(JSON.stringify(results));
  `, JSON.stringify(invalidPorts)], {
    cwd: fileURLToPath(root), env: { ...process.env }, encoding: 'utf8', timeout: 15_000,
  });
  assert.equal(result.error, undefined, 'invalid config imports must finish within their bound');
  assert.equal(result.status, 0, result.stderr);
  const results = JSON.parse(result.stdout);
  assert.equal(results.length, invalidPorts.length);
  for (const [index, observation] of results.entries()) {
    assert.equal(observation.rejected, true, `invalid port case ${index} must be rejected`);
    assert.equal(observation.message,
      'ORGMETRA_WORKSPACE_PORT must be a canonical decimal TCP port from 1 to 65535');
  }
});

/** Check dependency provisioning in the owning workflows' canonical step blocks. */
function assertValidationDependencies(workflowPath) {
  const workflow = readFileSync(new URL(workflowPath, root), 'utf8');
  const steps = workflow.split(/^      - /m).slice(1);
  const validateIndex = steps.findIndex((step) => /^        run: npm run validate$/m.test(step));
  const installIndex = steps.findIndex((step) => /^        run: npm ci$/m.test(step));
  assert.ok(validateIndex >= 0, `${workflowPath} must retain npm run validate`);
  assert.ok(installIndex >= 0 && installIndex < validateIndex,
    `${workflowPath} must provision npm ci before the first npm run validate`);
  const install = steps[installIndex];
  assert.doesNotMatch(install, /^        (?:if|continue-on-error):/m,
    'dependency installation must be unconditional and fail closed');
  const setupIndex = steps.findIndex((step) =>
    /uses: actions\/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020\b/.test(step)
    && /^          node-version: "24"$/m.test(step)
    && /^          check-latest: false$/m.test(step));
  assert.ok(setupIndex >= 0 && setupIndex < installIndex,
    `${workflowPath} must set up pinned Node 24 before npm ci`);
}

test('Foundation provisions reviewed Node dependencies before repository validation', () => {
  assertValidationDependencies('.github/workflows/foundation-ci.yml');
});

test('Recovery provisions reviewed runtimes and Node dependencies before repository validation', () => {
  const workflowPath = '.github/workflows/recovery-rehearsal-quality.yml';
  assertValidationDependencies(workflowPath);
  const workflow = readFileSync(new URL(workflowPath, root), 'utf8');
  const steps = workflow.split(/^      - /m).slice(1);
  const setupIndex = steps.findIndex((step) =>
    /uses: actions\/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97\b/.test(step)
    && /^          python-version: "3\.14"$/m.test(step)
    && /^          check-latest: false$/m.test(step));
  const consumerIndex = steps.findIndex((step) => /^          python - <<'PY'$/m.test(step));
  assert.ok(consumerIndex >= 0, 'Recovery must retain its Python provenance consumer');
  assert.ok(setupIndex >= 0 && setupIndex < consumerIndex,
    'Recovery must provision pinned Python 3.14 before its first Python consumer');
});

test('the retained workspace executes browser acceptance in canonical Foundation without a second quality owner', () => {
  const workflow = readFileSync(new URL('.github/workflows/foundation-ci.yml', root), 'utf8');
  assert.equal(existsSync(new URL('.github/workflows/hr-workspace-browser-e2e.yml', root)), false);
  assert.equal(existsSync(new URL('.github/workflows/job-analysis-api-quality.yml', root)), false);
  assert.match(workflow, /npx playwright install --with-deps chromium/);
  assert.match(workflow, /npm run test:e2e/);
  assert.match(workflow, /npm run build-storybook/);
  assert.match(workflow, /Run PostgreSQL contracts in isolated containers/);
  assert.match(workflow, /git diff --exit-code/);
});
