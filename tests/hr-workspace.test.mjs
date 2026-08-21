import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
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
  for (const storyName of ['ActionButtons', 'FieldStates', 'PermissionDenied', 'EvidenceDrawer', 'HighRiskConfirmation', 'AssignmentSplit']) {
    assert.match(story, new RegExp(`export const ${storyName}`));
  }
  assert.match(story, /orgmetra-action-request-evidence/);
  assert.match(story, /Exact assignment allocation values/);
  assert.match(story, /aria-invalid="true"/);
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
