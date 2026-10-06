import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';
import { jobAnalysisApiFixture } from './job-analysis-api-fixture.mjs';
import {
  fetchJobAnalysisSnapshot,
  fetchPeopleRecord,
  isPurposeAuthorized,
  jobAnalysisSnapshotUrl,
  nextLocale,
  peopleRecordUrl,
} from '../apps/hr-workspace/app.js';

const html = readFileSync(new URL('../apps/hr-workspace/index.html', import.meta.url), 'utf8');
const css = readFileSync(new URL('../apps/hr-workspace/styles.css', import.meta.url), 'utf8');
const app = readFileSync(new URL('../apps/hr-workspace/app.js', import.meta.url), 'utf8');
const story = readFileSync(new URL('../apps/hr-workspace/workspace.stories.js', import.meta.url), 'utf8');
const storybookConfig = readFileSync(new URL('../.storybook/main.js', import.meta.url), 'utf8');
const storybookPreview = readFileSync(new URL('../.storybook/preview.js', import.meta.url), 'utf8');

test('workspace exposes the Figma role slice and existing design tokens', () => {
  assert.match(html, /packages\/design-tokens\/tokens\.css/);
  assert.match(html, /data-node-id="1:10"/);
  assert.match(html, /data-node-id="1:28"/);
  assert.match(html, /data-view-link="hr-home"/);
  assert.match(html, /data-view-link="employee-profile"/);
  assert.match(html, /data-view-link="job-analysis"/);
  assert.match(html, /id="people-api-form"/);
  assert.match(css, /var\(--orgmetra-action-review\)/);
  assert.match(css, /var\(--orgmetra-focus-ring\)/);
});

test('workspace includes keyboard-accessible review and high-impact states', () => {
  assert.match(html, /id="evidence-dialog"/);
  assert.match(html, /id="confirmation-dialog"/);
  assert.match(html, /role="alert"/);
  assert.match(html, /role="status"/);
  assert.match(html, /aria-label="Close"/);
  assert.match(html, /required rows="3"/);
  assert.match(html, /Exact assignment allocation values/);
});

test('locale-sensitive icon controls translate their accessible names', () => {
  assert.match(
    html,
    /id="locale-toggle"[^>]*data-i18n-aria-label="changeLanguage"/,
    'language toggle needs a locale-bound accessible name',
  );
  assert.equal(
    (html.match(/data-i18n-aria-label="close"/g) ?? []).length,
    2,
    'both icon-only dialog close buttons need locale-bound accessible names',
  );
  assert.match(app, /querySelectorAll\('\[data-i18n-aria-label\]'\)/);
  assert.match(app, /dictionary\[element\.dataset\.i18nAriaLabel\]/);
});

test('Storybook exposes tokenized workspace states without claiming API connectivity', () => {
  assert.match(storybookConfig, /@storybook\/web-components-vite/);
  assert.match(storybookPreview, /design-tokens\/tokens\.css/);
  for (const storyName of [
    'ActionButtons',
    'FieldStates',
    'PermissionDenied',
    'EvidenceDrawer',
    'HighRiskConfirmation',
    'AssignmentSplit',
    'PeopleNotConnected',
    'JobAnalysisNotConnected',
  ]) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /orgmetra-action-request-evidence/);
  assert.match(story, /Exact assignment allocation values/);
  assert.match(story, /aria-invalid="true"/);
  assert.match(story, /data-figma-node-id="2:2"/);
  assert.match(story, /Connect the host before loading protected data/);
  assert.match(story, /No local fallback is used/);
});

test('purpose and locale transitions preserve the trust boundary', () => {
  assert.equal(isPurposeAuthorized('hr_operations'), true);
  assert.equal(isPurposeAuthorized('recruiting'), false);
  assert.equal(nextLocale('en'), 'ko');
  assert.equal(nextLocale('ko'), 'en');
  assert.match(app, /no API mutation was sent/);
  assert.doesNotMatch(html, /password|passkey_value|private_key/i);
});

test('Job Analysis uses a host authorization provider without persisting bearer material', async () => {
  const config = {
    baseUrl: 'https://job-analysis.example.test/',
    tenantRecordId: 'tenant/alpha',
    analysisRecordId: 'analysis-1',
    purposeCode: 'job_analysis_read',
    getAuthorization: async () => 'Bearer host-provided-token',
  };
  assert.equal(
    jobAnalysisSnapshotUrl(config),
    'https://job-analysis.example.test/v1/tenants/tenant%2Falpha/job-analysis-snapshots/analysis-1',
  );
  let request;
  const snapshot = await fetchJobAnalysisSnapshot(config, async (url, options) => {
    request = { url, options };
    return { ok: true, status: 200, json: async () => ({ analysis_record_id: 'analysis-1' }) };
  });
  assert.deepEqual(snapshot, { analysis_record_id: 'analysis-1' });
  assert.equal(request.url, jobAnalysisSnapshotUrl(config));
  assert.equal(request.options.credentials, 'omit');
  assert.equal(request.options.headers.Authorization, 'Bearer host-provided-token');
  assert.equal(request.options.headers['X-Purpose-Code'], 'job_analysis_read');
  assert.doesNotMatch(html, /localStorage|sessionStorage|authorization.*input/i);
});

test('Job Analysis renders the authoritative API document without a whole-snapshot digest', async () => {
  const snapshot = jobAnalysisApiFixture();
  assert.equal(Object.hasOwn(snapshot, 'content_digest_sha256'), false);
  assert.equal(snapshot.tasks.length, 3);
  assert.equal(snapshot.ksao_requirements.length, 3);
  assert.match(snapshot.tasks[0].source.content_digest_sha256, /^[a-f0-9]{64}$/);

  const payload = await fetchJobAnalysisSnapshot({
    baseUrl: 'https://job-analysis.example.test',
    tenantRecordId: snapshot.tenant_record_id,
    analysisRecordId: snapshot.analysis_record_id,
    getAuthorization: () => 'Bearer fixture-host-token',
  }, async () => ({ ok: true, status: 200, json: async () => snapshot }));
  const nodes = Object.fromEntries([
    'result', 'analysis-id', 'state', 'effective', 'recorded', 'task-count', 'ksao-count',
  ].map((suffix) => [`job-analysis-${suffix}`, { textContent: '', hidden: true }]));
  const context = {
    document: {
      getElementById(id) {
        assert.ok(Object.hasOwn(nodes, id), `unsupported Job Analysis field: ${id}`);
        return nodes[id];
      },
    },
    snapshot: payload,
  };
  for (const name of ['clearJobAnalysisSnapshot', 'renderJobAnalysisSnapshot']) {
    const source = app.match(new RegExp(`^function ${name}\\([^]*?^\\}`, 'm'));
    assert.ok(source, `retained ${name} function must be exercised`);
    runInNewContext(`${source[0]}\n${name}(${name.startsWith('render') ? 'snapshot' : ''});`, context);
  }
  for (const [suffix, expected] of Object.entries({
    'analysis-id': snapshot.analysis_record_id,
    state: snapshot.status_code,
    effective: snapshot.effective_from,
    recorded: snapshot.recorded_at,
    'task-count': '3',
    'ksao-count': '3',
  })) {
    assert.match(html, new RegExp(`id="job-analysis-${suffix}"`));
    assert.equal(nodes[`job-analysis-${suffix}`].textContent, expected);
  }
  assert.equal(nodes['job-analysis-result'].hidden, false);
  assert.doesNotMatch(html, /jobAnalysisDigest|job-analysis-digest/);
  assert.doesNotMatch(app, /jobAnalysisDigest|job-analysis-digest|content_digest_sha256/);
});

test('browser Job Analysis mock uses the same authoritative document and retains the canonical timeout', () => {
  const browser = readFileSync(new URL('./e2e/hr-workspace.spec.mjs', import.meta.url), 'utf8');
  const config = readFileSync(new URL('../playwright.config.mjs', import.meta.url), 'utf8');
  assert.match(browser, /import \{ jobAnalysisApiFixture \} from '\.\.\/job-analysis-api-fixture\.mjs'/);
  assert.match(browser, /const jobAnalysisSnapshot = jobAnalysisApiFixture\(\)/);
  assert.match(browser, /body: JSON\.stringify\(jobAnalysisSnapshot\)/);
  assert.doesNotMatch(browser, /content_digest_sha256:|task_id:|ksao_id:/);
  assert.match(config, /timeout: 15_000/);
});

test('gap baseline traceability names its active-PR maturity and governing ADR', () => {
  const traceability = readFileSync(new URL('../docs/TRACEABILITY.md', import.meta.url), 'utf8');
  const adr = readFileSync(new URL('../docs/adr/0026-product-technical-gap-baseline.md', import.meta.url), 'utf8');
  const row = traceability.split('\n').filter((line) => line.startsWith('| Product and technical gap baseline |'));
  assert.equal(row.length, 1, 'the gap baseline has one source-contract row');
  const cells = row[0].split('|').map((cell) => cell.trim());
  assert.match(adr, /^# ADR 0026: Product and technical gap baseline/m);
  assert.match(adr, /`docs\/product-technical-gap-baseline\.md` is the current evidence ledger/);
  assert.equal(cells[6], 'implemented_on_active_pr', 'local candidate documentation is not protected truth');
  assert.equal(cells[5], 'ADR-0026', 'the baseline is not governed by the workspace ADR');
});

test('People API uses host authorization and an explicit no-storage read boundary', async () => {
  const config = {
    baseUrl: 'https://people.example.test/',
    tenantRecordId: 'tenant/alpha',
    personRecordId: 'person-1',
    effectiveOn: '2026-08-21',
    purposeCode: 'people_read',
    requestedFields: ['display_name', 'employment_status_code'],
    getAuthorization: async () => 'Bearer host-provided-token',
  };
  assert.equal(
    peopleRecordUrl(config),
    'https://people.example.test/v1/tenants/tenant%2Falpha/people/person-1?effective_on=2026-08-21&purpose=people_read&fields=display_name%2Cemployment_status_code',
  );
  let request;
  const record = await fetchPeopleRecord(config, async (url, options) => {
    request = { url, options };
    return { ok: true, status: 200, json: async () => ({ fields: { display_name: 'Authorized worker', employment_status_code: 'active' } }) };
  });
  assert.deepEqual(record.fields, { display_name: 'Authorized worker', employment_status_code: 'active' });
  assert.equal(request.url, peopleRecordUrl(config));
  assert.equal(request.options.credentials, 'omit');
  assert.equal(request.options.headers.Authorization, 'Bearer host-provided-token');
  assert.doesNotMatch(html, /localStorage|sessionStorage|authorization.*input/i);
});

/** Execute the unchanged workspace handlers with an explicitly held synthetic transport. */
function protectedReadWorkspace() {
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, {
      value: '', hidden: true, textContent: '', dataset: {}, handlers: {},
      addEventListener(type, callback) { this.handlers[type] = callback; },
      setAttribute() {}, focus() {},
    });
    return nodes.get(id);
  };
  const pending = [];
  const context = {
    URLSearchParams,
    document: {
      documentElement: { dataset: {}, lang: '' },
      getElementById: node, querySelector: node, querySelectorAll: () => [],
      addEventListener(type, callback) { node('document').addEventListener(type, callback); },
    },
    __ORGMETRA_PEOPLE__: {
      baseUrl: 'https://people.example.test', tenantRecordId: 'tenant-fixture',
      personRecordId: 'person-fixture', effectiveOn: '2026-10-04',
      purposeCode: 'people_read', requestedFields: ['display_name'],
      getAuthorization: () => 'Bearer fixture-only',
    },
    __ORGMETRA_JOB_ANALYSIS__: {
      baseUrl: 'https://job.example.test', tenantRecordId: 'tenant-fixture',
      analysisRecordId: 'analysis-fixture', purposeCode: 'job_analysis_read',
      getAuthorization: () => 'Bearer fixture-only',
    },
    fetch: () => new Promise((resolve) => pending.push(resolve)),
  };
  runInNewContext(app.replace(/^export /gm, ''), context);
  return { node, pending, context };
}

test('personal-details purpose edits clear the previous access result until an explicit review', () => {
  for (const eventType of ['input', 'change']) {
    const { node } = protectedReadWorkspace();
    const purpose = node('access-purpose');
    const review = node('[data-action="view-personal-details"]');
    purpose.value = 'hr_operations';
    review.handlers.click();
    assert.equal(node('details-panel').hidden, false, 'the permitted fixture review must show its result');
    purpose.value = 'recruiting';
    purpose.handlers[eventType]?.({ target: purpose });
    assert.equal(node('details-panel').hidden, true, `${eventType}: the previous purpose result must not remain visible`);
    assert.equal(node('permission-panel').hidden, true, 'editing is not a new denied review');
    review.handlers.click();
    assert.equal(node('permission-panel').hidden, false, 'an explicit denied review must still explain the refusal');
    purpose.value = 'hr_operations';
    purpose.handlers[eventType]?.({ target: purpose });
    assert.equal(node('permission-panel').hidden, true, 'the previous denial must also be invalidated');
    assert.equal(node('details-panel').hidden, true, 'returning to a permitted purpose does not perform a review');
    review.handlers.click();
    assert.equal(node('details-panel').hidden, false, 'a fresh explicit permitted review must recover');
  }
});

test('host authority invalidation synchronously clears both loaded read surfaces', async () => {
  const { node, pending } = protectedReadWorkspace();
  const people = node('people-api-form').handlers.submit({ preventDefault() {} });
  const job = node('job-analysis-form').handlers.submit({ preventDefault() {} });
  await Promise.resolve();
  assert.equal(pending.length, 2);
  pending[0]({ status: 200, ok: true, json: async () => ({ fields: { display_name: 'Previous authority', employment_status_code: 'active' } }) });
  pending[1]({ status: 200, ok: true, json: async () => ({ analysis_record_id: 'previous-analysis', status_code: 'approved', effective_from: '2026-10-04', recorded_at: 'previous-cutoff', tasks: [1], ksao_requirements: [1] }) });
  await Promise.all([people, job]);
  assert.equal(node('people-api-result').hidden, false);
  assert.equal(node('job-analysis-result').hidden, false);
  node('document').handlers['orgmetra:authority-invalidated']?.();
  for (const prefix of ['people-api', 'job-analysis']) {
    assert.equal(node(`${prefix}-result`).hidden, true, `${prefix}: the old authority's result must be hidden synchronously`);
    assert.equal(node(`${prefix}-status`).dataset.state, 'idle');
  }
  for (const id of ['people-api-display-name', 'people-api-employment-status', 'job-analysis-analysis-id', 'job-analysis-state', 'job-analysis-effective', 'job-analysis-recorded']) {
    assert.equal(node(id).textContent, 'unknown', `${id}: old values must be erased, not only hidden`);
  }
  for (const id of ['job-analysis-task-count', 'job-analysis-ksao-count']) assert.equal(node(id).textContent, '0');
  assert.equal(pending.length, 2, 'invalidation must not dispatch another request');
});

const protectedReadCases = [
  {
    kind: 'People', form: 'people-api-form', result: 'people-api-result', status: 'people-api-status',
    coordinates: ['people-api-tenant', 'people-api-person', 'people-api-effective', 'people-api-purpose', 'people-api-fields'],
    payload: { fields: { display_name: 'Original worker', employment_status_code: 'active' } },
    clearedField: 'people-api-display-name',
  },
  {
    kind: 'Job Analysis', form: 'job-analysis-form', result: 'job-analysis-result', status: 'job-analysis-status',
    coordinates: ['job-analysis-tenant', 'job-analysis-record', 'job-analysis-purpose'],
    payload: { analysis_record_id: 'analysis-fixture', status_code: 'approved', tasks: [], ksao_requirements: [] },
    clearedField: 'job-analysis-analysis-id',
  },
];

for (const fixture of protectedReadCases) {
  for (const transition of [
    'authority', 'repeated-authority', 'authority-away-back', 'newer-submit',
    ...fixture.coordinates.flatMap((coordinate) => ['input', 'change'].map((eventType) => `${coordinate}/${eventType}`)),
  ]) {
    for (const outcome of ['credential', 'provider-rejection', 'no-credential']) {
      test(`${fixture.kind} credential wait: ${transition}/${outcome} cannot dispatch or overwrite a newer read`, async () => {
        const { node, context } = protectedReadWorkspace();
        const host = fixture.kind === 'People' ? context.__ORGMETRA_PEOPLE__ : context.__ORGMETRA_JOB_ANALYSIS__;
        let releaseCredential;
        let rejectCredential;
        const heldCredential = new Promise((resolve, reject) => {
          releaseCredential = resolve;
          rejectCredential = reject;
        });
        const providerCoordinates = [];
        host.getAuthorization = function () {
          providerCoordinates.push({
            tenant: this.tenantRecordId,
            record: this.personRecordId || this.analysisRecordId,
          });
          return providerCoordinates.length === 1 ? heldCredential : 'Bearer current-fixture-only';
        };
        const freshPayload = fixture.kind === 'People'
          ? { fields: { display_name: 'Current credential worker', employment_status_code: 'active' } }
          : { ...fixture.payload, analysis_record_id: 'current-credential-analysis', tasks: [1], ksao_requirements: [1] };
        const sent = [];
        context.fetch = async (url, options) => {
          assert.equal(options.credentials, 'omit');
          if (fixture.kind === 'Job Analysis') assert.equal(options.headers['X-Purpose-Code'], host.purposeCode);
          // Synthetic headers are inspected here, never copied into retained observations.
          assert.ok(['Bearer current-fixture-only', 'Bearer obsolete-fixture-only'].includes(options.headers.Authorization));
          sent.push(url);
          return { status: 200, ok: true, json: async () => freshPayload };
        };
        const form = node(fixture.form);
        const submit = () => form.handlers.submit({ preventDefault() {} });
        const previous = submit();
        assert.equal(providerCoordinates.length, 1, 'the real handler must enter the held provider');
        assert.equal(sent.length, 0, 'credential acquisition is not transport admission');
        const invalidate = node('document').handlers['orgmetra:authority-invalidated'];
        if (transition === 'authority' || transition === 'repeated-authority') {
          invalidate();
          if (transition === 'repeated-authority') invalidate();
        } else if (transition === 'authority-away-back') {
          invalidate();
          host.tenantRecordId = 'away-tenant';
          invalidate();
          host.tenantRecordId = 'tenant-fixture';
        } else if (transition !== 'newer-submit') {
          const [coordinate, eventType] = transition.split('/');
          const input = node(coordinate);
          const original = input.value;
          input.value = 'changed-coordinate';
          form.handlers[eventType]({ target: input });
          input.value = original;
          form.handlers[eventType]({ target: input });
        }
        if (transition !== 'newer-submit') {
          assert.equal(node(fixture.result).hidden, true);
          assert.equal(node(fixture.clearedField).textContent, 'unknown');
          assert.equal(node(fixture.status).dataset.state, 'idle');
        }
        assert.equal(sent.length, 0, 'invalidation and coordinate reversion cannot perform a read');
        await submit();
        assert.equal(sent.length, 1, 'the new explicit current read must dispatch exactly once');
        const expectedUrl = fixture.kind === 'People' ? peopleRecordUrl(host) : jobAnalysisSnapshotUrl(host);
        assert.equal(sent[0], expectedUrl, 'the original provider and request coordinates must be retained');
        assert.deepEqual(providerCoordinates, [
          { tenant: 'tenant-fixture', record: fixture.kind === 'People' ? 'person-fixture' : 'analysis-fixture' },
          { tenant: 'tenant-fixture', record: fixture.kind === 'People' ? 'person-fixture' : 'analysis-fixture' },
        ]);
        const currentValue = node(fixture.clearedField).textContent;
        const currentStatus = node(fixture.status).textContent;
        assert.equal(currentValue, fixture.kind === 'People' ? 'Current credential worker' : 'current-credential-analysis');
        assert.equal(node(fixture.result).hidden, false, 'the nonempty current authorized result must render');
        if (fixture.kind === 'Job Analysis') assert.equal(node('job-analysis-task-count').textContent, '1');
        if (outcome === 'provider-rejection') rejectCredential(new Error('synthetic provider failure'));
        else releaseCredential(outcome === 'no-credential' ? '' : 'Bearer obsolete-fixture-only');
        await previous;
        assert.equal(sent.length, 1, 'obsolete credential-waiting submission must send zero requests');
        assert.equal(node(fixture.result).hidden, false, 'obsolete settlement must not clear the newest read');
        assert.equal(node(fixture.clearedField).textContent, currentValue);
        assert.equal(node(fixture.status).textContent, currentStatus);
        assert.equal(node(fixture.status).dataset.state, 'loaded');
      });
    }
  }

  test(`${fixture.kind} authority invalidation fences old response outcomes and preserves fresh reads`, async () => {
    for (const outcome of ['success', 'body', 'denial', 'body-error']) {
      const { node, pending, context } = protectedReadWorkspace();
      let authority = 'previous';
      const observedAuthorities = [];
      const config = fixture.kind === 'People' ? context.__ORGMETRA_PEOPLE__ : context.__ORGMETRA_JOB_ANALYSIS__;
      config.getAuthorization = () => {
        observedAuthorities.push(authority);
        return 'Bearer fixture-only';
      };
      const submit = () => node(fixture.form).handlers.submit({ preventDefault() {} });
      const previous = submit();
      await Promise.resolve();
      assert.equal(pending.length, 1);
      let releaseBody;
      if (outcome === 'body') {
        let markBody;
        const entered = new Promise((resolve) => { markBody = resolve; });
        const body = new Promise((resolve) => { releaseBody = resolve; });
        pending[0]({ status: 200, ok: true, json: () => { markBody(); return body; } });
        await entered;
      }
      const invalidate = node('document').handlers['orgmetra:authority-invalidated'];
      assert.equal(typeof invalidate, 'function', 'the documented host event must be wired');
      invalidate();
      invalidate();
      assert.equal(node(fixture.result).hidden, true);
      assert.equal(node(fixture.clearedField).textContent, 'unknown');
      assert.equal(node(fixture.status).dataset.state, 'idle');
      assert.equal(pending.length, 1, 'repeated invalidation cannot perform a read');
      authority = 'current';
      const fresh = submit();
      await Promise.resolve();
      const freshPayload = fixture.kind === 'People'
        ? { fields: { display_name: 'Current authority worker', employment_status_code: 'active' } }
        : { ...fixture.payload, analysis_record_id: 'current-authority-analysis' };
      pending[1]({ status: 200, ok: true, json: async () => freshPayload });
      await fresh;
      assert.deepEqual(observedAuthorities, ['previous', 'current']);
      assert.equal(node(fixture.result).hidden, false, 'a new explicit authorized read must remain usable');
      const currentValue = node(fixture.clearedField).textContent;
      assert.equal(currentValue, fixture.kind === 'People' ? 'Current authority worker' : 'current-authority-analysis');
      if (outcome === 'body') releaseBody(fixture.payload);
      else if (outcome === 'denial') pending[0]({ status: 403, ok: false });
      else pending[0]({ status: 200, ok: true, json: async () => {
        if (outcome === 'body-error') throw new Error('fixture body failure');
        return fixture.payload;
      } });
      await previous;
      assert.equal(node(fixture.result).hidden, false, `${outcome}: an old callback cannot hide the current read`);
      assert.equal(node(fixture.clearedField).textContent, currentValue);
      assert.equal(node(fixture.status).dataset.state, 'loaded');
      const denied = submit();
      await Promise.resolve();
      pending[2]({ status: 403, ok: false });
      await denied;
      assert.equal(node(fixture.result).hidden, true, 'current authority denial remains authoritative');
      assert.equal(node(fixture.status).dataset.state, 'error');
    }
  });

  test(`${fixture.kind} coordinate edits invalidate pending responses even after reverting`, async () => {
    for (const coordinate of fixture.coordinates) {
      for (const eventType of ['input', 'change']) {
        const { node, pending } = protectedReadWorkspace();
        const form = node(fixture.form);
        const submitted = form.handlers.submit({ preventDefault() {} });
        await Promise.resolve();
        assert.equal(pending.length, 1, 'the actual fetch boundary must be reached');
        const input = node(coordinate);
        const original = input.value;
        input.value = 'changed-coordinate';
        form.handlers[eventType]?.({ target: input });
        input.value = original;
        form.handlers[eventType]?.({ target: input });
        pending[0]({ status: 200, ok: true, json: async () => fixture.payload });
        await submitted;
        assert.equal(node(fixture.result).hidden, true, `${coordinate}/${eventType}: stale data must remain hidden`);
        assert.equal(node(fixture.clearedField).textContent, 'unknown');
        assert.equal(node(fixture.status).dataset.state, 'idle');
      }
    }
  });

  test(`${fixture.kind} coordinate edits clear loaded values and allow a fresh explicit read`, async () => {
    const { node, pending } = protectedReadWorkspace();
    const form = node(fixture.form);
    const submit = () => form.handlers.submit({ preventDefault() {} });
    const first = submit();
    await Promise.resolve();
    pending[0]({ status: 200, ok: true, json: async () => fixture.payload });
    await first;
    assert.equal(node(fixture.result).hidden, false, 'an unchanged authorized read must still render');
    node(fixture.coordinates[0]).value = 'changed-tenant';
    form.handlers.input?.({ target: node(fixture.coordinates[0]) });
    assert.equal(node(fixture.result).hidden, true, 'an edited form cannot retain the previous resource');
    assert.equal(node(fixture.clearedField).textContent, 'unknown');
    const fresh = submit();
    await Promise.resolve();
    assert.equal(pending.length, 2);
    pending[1]({ status: 200, ok: true, json: async () => fixture.payload });
    await fresh;
    assert.equal(node(fixture.result).hidden, false);
    assert.equal(node(fixture.status).dataset.state, 'loaded');
  });
}
