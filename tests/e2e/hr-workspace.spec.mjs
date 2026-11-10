import { expect, test } from '@playwright/test';
import { jobAnalysisApiFixture } from '../job-analysis-api-fixture.mjs';

const jobAnalysisSnapshot = jobAnalysisApiFixture();

const workspacePath = '/apps/hr-workspace/index.html';

/** Install synthetic host authorization and API coordinates before loading the browser fixture. */
async function injectProtectedReadConfig(page) {
  await page.addInitScript((snapshot) => {
    const baseUrl = window.location.origin;
    /** Return the synthetic test credential; the validation-order fixture also counts requests for it. */
    const getAuthorization = () => 'Bearer e2e-host-token';
    window.__ORGMETRA_JOB_ANALYSIS__ = {
      baseUrl,
      tenantRecordId: snapshot.tenant_record_id,
      analysisRecordId: snapshot.analysis_record_id,
      purposeCode: 'job_analysis_read',
      getAuthorization,
    };
    window.__ORGMETRA_PEOPLE__ = {
      baseUrl,
      tenantRecordId: 'tenant-e2e',
      personRecordId: 'person-e2e',
      effectiveOn: '2026-08-21',
      purposeCode: 'people_read',
      requestedFields: ['display_name', 'employment_status_code'],
      getAuthorization,
    };
  }, jobAnalysisSnapshot);
}

test('action buttons distinguish disabled and loading states across variants', async ({ page }) => {
  await page.goto(workspacePath);
  await page.evaluate(async () => {
    const { ActionButtons } = await import('/apps/hr-workspace/workspace.stories.js');
    document.body.innerHTML = ActionButtons.render();
    const controls = document.createElement('div');
    controls.innerHTML = ['button', 'button button-review', 'button button-secondary'].map((classes) =>
      `<button class="${classes}">Enabled</button><button class="${classes}" disabled>Disabled</button><button class="${classes}" aria-busy="true">Loading</button>`
    ).join('');
    document.body.append(controls);
  });
  const buttons = page.locator('.button');
  for (let index = 0; index < await buttons.count(); index += 1) {
    const button = buttons.nth(index);
    const inactive = await button.evaluate((node) => node.disabled || node.getAttribute('aria-busy') === 'true');
    await expect(button).toHaveCSS('opacity', inactive ? '0.55' : '1');
    await expect(button).toHaveCSS('cursor', inactive ? 'not-allowed' : 'pointer');
  }
});

test('human-review workspace states remain keyboard-accessible and localized', async ({ page }) => {
  await page.goto(workspacePath);

  await expect(page.getByRole('heading', { name: 'HR Home' })).toBeVisible();
  const localeToggle = page.locator('#locale-toggle');
  await expect(localeToggle).toHaveText('한국어');
  await expect(localeToggle).toHaveAccessibleName('Change language to 한국어');
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await expect(page.getByRole('heading', { name: 'Employee Profile' })).toBeVisible();

  await page.locator('#access-purpose').selectOption('recruiting');
  await page.locator('[data-action="view-personal-details"]').click();
  await expect(page.locator('#permission-panel')).toBeVisible();
  await expect(page.locator('#details-panel')).toBeHidden();

  await page.locator('#access-purpose').selectOption('hr_operations');
  await page.locator('[data-action="view-personal-details"]').click();
  await expect(page.locator('#details-panel')).toBeVisible();
  await expect(page.locator('#permission-panel')).toBeHidden();

  await localeToggle.click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ko');
  await expect(page.getByRole('heading', { name: '직원 프로필' })).toBeVisible();
  await expect(localeToggle).toHaveText('English');
  await expect(localeToggle).toHaveAccessibleName('언어를 English로 변경');

  await page.locator('[data-action="correct-history"]').click();
  const confirmationDialog = page.locator('#confirmation-dialog');
  await expect(confirmationDialog).toBeVisible();
  await page.locator('#confirm-correction').click();
  await expect(page.locator('#confirmation-reason')).toBeFocused();
  await page.locator('#confirmation-reason').fill('Review the effective-date evidence before correction.');
  await page.locator('#confirm-correction').click();
  await expect(page.locator('#confirmation-status')).toBeVisible();
  await expect(page.locator('#confirmation-status')).toContainText('정정 초안을 확인');

  await page.getByRole('button', { name: '취소' }).click();
  await expect(confirmationDialog).toBeHidden();
  await page.locator('[data-action="correct-history"]').click();
  await expect(confirmationDialog).toBeVisible();
  await expect(page.locator('#confirmation-status')).toBeHidden();
  await expect(page.locator('#confirmation-reason')).toHaveValue('');
});

test('Cancel dismisses correction with an empty required reason', async ({ page }) => {
  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.locator('[data-action="correct-history"]').click();
  const dialog = page.locator('#confirmation-dialog');
  await expect(dialog).toBeVisible();
  await expect(page.locator('#confirmation-reason')).toHaveValue('');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('#confirmation-status')).toHaveJSProperty('hidden', true);
  await expect(dialog).toHaveJSProperty('returnValue', 'cancel');
});

test('Close dismisses correction with an empty required reason', async ({ page }) => {
  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.locator('[data-action="correct-history"]').click();
  const dialog = page.locator('#confirmation-dialog');
  await expect(dialog).toBeVisible();
  await expect(page.locator('#confirmation-reason')).toHaveValue('');
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('#confirmation-status')).toHaveJSProperty('hidden', true);
  await expect(dialog).toHaveJSProperty('returnValue', 'cancel');
});

for (const { name, reason, valueMissing } of [
  { name: 'empty', reason: '', valueMissing: true },
  { name: 'whitespace-only', reason: ' \n\t ', valueMissing: false },
]) {
  test(`Confirmation rejects a ${name} correction reason`, async ({ page }) => {
    await page.goto(workspacePath);
    await page.locator('[data-view-link="employee-profile"]').first().click();
    await page.locator('[data-action="correct-history"]').click();
    const dialog = page.locator('#confirmation-dialog');
    const reasonInput = page.locator('#confirmation-reason');
    const confirmButton = page.locator('#confirm-correction');
    await expect(reasonInput).toHaveJSProperty('required', true);
    await expect(page.locator('#confirmation-form')).toHaveJSProperty('noValidate', false);
    await expect(confirmButton).toHaveJSProperty('formNoValidate', false);
    await reasonInput.fill(reason);
    await expect(reasonInput).toHaveValue(reason);
    expect(await reasonInput.evaluate((input) => input.validity.valueMissing)).toBe(valueMissing);
    await confirmButton.click();
    await expect(dialog).toBeVisible();
    await expect(reasonInput).toBeFocused();
    await expect(page.locator('#confirmation-status')).toHaveJSProperty('hidden', true);
    await expect(dialog).toHaveJSProperty('returnValue', '');
  });
}

test('unconfigured protected reads stay neutral and explain the host next action', async ({ page }) => {
  await page.goto(workspacePath);

  await page.locator('[data-view-link="employee-profile"]').first().click();
  const peopleStatus = page.locator('#people-api-status');
  await expect(peopleStatus).toHaveAttribute('data-state', 'not-configured');
  await expect(peopleStatus).toContainText('host must provide a People API URL and authorization provider');
  await page.getByRole('button', { name: 'Load worker record' }).click();
  await expect(peopleStatus).toHaveAttribute('data-state', 'not-configured');
  await expect(page.locator('#people-api-result')).toBeHidden();

  await page.locator('[data-view-link="job-analysis"]').first().click();
  const jobAnalysisStatus = page.locator('#job-analysis-status');
  await expect(jobAnalysisStatus).toHaveAttribute('data-state', 'not-configured');
  await expect(jobAnalysisStatus).toContainText('host must provide an API base URL and authorization provider');
  await page.getByRole('button', { name: 'Load snapshot' }).click();
  await expect(jobAnalysisStatus).toHaveAttribute('data-state', 'not-configured');
  await expect(page.locator('#job-analysis-result')).toBeHidden();
});

test('connected read views use host authorization and render API evidence', async ({ page }) => {
  await injectProtectedReadConfig(page);
  const requests = [];
  await page.route('**/v1/tenants/**/people/**', async (route) => {
    const request = route.request();
    requests.push({
      kind: 'people',
      url: request.url(),
      authorization: (await request.headers()).authorization,
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ fields: { display_name: 'E2E authorized worker', employment_status_code: 'active' } }),
    });
  });
  await page.route('**/v1/tenants/**/job-analysis-snapshots/**', async (route) => {
    const request = route.request();
    requests.push({
      kind: 'job-analysis',
      url: request.url(),
      authorization: (await request.headers()).authorization,
      purpose: (await request.headers())['x-purpose-code'],
    });
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(jobAnalysisSnapshot),
    });
  });

  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.getByRole('button', { name: 'Load worker record' }).click();
  await expect(page.locator('#people-api-status')).toHaveAttribute('data-state', 'loaded');
  await expect(page.locator('#people-api-display-name')).toHaveText('E2E authorized worker');
  await expect(page.locator('#people-api-employment-status')).toHaveText('active');

  await page.locator('[data-view-link="job-analysis"]').first().click();
  await page.getByRole('button', { name: 'Load snapshot' }).click();
  await expect(page.locator('#job-analysis-status')).toHaveAttribute('data-state', 'loaded');
  await expect(page.locator('#job-analysis-task-count')).toHaveText(String(jobAnalysisSnapshot.tasks.length));
  await expect(page.locator('#job-analysis-ksao-count')).toHaveText(String(jobAnalysisSnapshot.ksao_requirements.length));

  const peopleRequest = requests.find((request) => request.kind === 'people');
  const peopleUrl = new URL(peopleRequest.url);
  expect(peopleRequest.authorization).toBe('Bearer e2e-host-token');
  expect(peopleUrl.searchParams.get('effective_on')).toBe('2026-08-21');
  expect(peopleUrl.searchParams.get('purpose')).toBe('people_read');
  expect(peopleUrl.searchParams.get('fields')).toBe('display_name,employment_status_code');

  const jobAnalysisRequest = requests.find((request) => request.kind === 'job-analysis');
  expect(jobAnalysisRequest.authorization).toBe('Bearer e2e-host-token');
  expect(jobAnalysisRequest.purpose).toBe('job_analysis_read');
});

test('denied protected reads show an actionable error without local fallback', async ({ page }) => {
  await injectProtectedReadConfig(page);
  await page.route('**/v1/tenants/**/people/**', async (route) => {
    await route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({ error_code: 'access_denied', message: 'denied' }),
    });
  });

  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.getByRole('button', { name: 'Load worker record' }).click();
  await expect(page.locator('#people-api-status')).toHaveAttribute('data-state', 'error');
  await expect(page.locator('#people-api-status')).toContainText('denied');
  await expect(page.locator('#people-api-result')).toBeHidden();
  await expect(page.locator('#people-api-display-name')).toHaveText('unknown');
});

test('a denied People reread removes previously authorized fields before the response settles', async ({ page }) => {
  await injectProtectedReadConfig(page);
  let requestCount = 0;
  await page.route('**/v1/tenants/**/people/**', async (route) => {
    requestCount += 1;
    if (requestCount === 1) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ fields: { display_name: 'Previously authorized worker', employment_status_code: 'active' } }),
      });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({ error_code: 'access_denied', message: 'denied' }),
    });
  });

  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  const loadButton = page.getByRole('button', { name: 'Load worker record' });
  await loadButton.click();
  await expect(page.locator('#people-api-result')).toBeVisible();
  await expect(page.locator('#people-api-display-name')).toHaveText('Previously authorized worker');

  await loadButton.click();
  await expect(page.locator('#people-api-result')).toBeHidden();
  await expect(page.locator('#people-api-display-name')).toHaveText('unknown');
  await expect(page.locator('#people-api-status')).toHaveAttribute('data-state', 'error');
  await expect(page.locator('#people-api-result')).toBeHidden();
});

test('only the latest People read may render when responses complete out of order', async ({ page }) => {
  await injectProtectedReadConfig(page);
  let requestCount = 0;
  let markFirstRequestSeen;
  const firstRequestSeen = new Promise((resolve) => {
    markFirstRequestSeen = resolve;
  });
  await page.route('**/v1/tenants/**/people/**', async (route) => {
    requestCount += 1;
    if (requestCount === 1) {
      markFirstRequestSeen();
      await new Promise((resolve) => setTimeout(resolve, 200));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ fields: { display_name: 'Stale worker', employment_status_code: 'inactive' } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ fields: { display_name: 'Latest worker', employment_status_code: 'active' } }),
    });
  });

  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  const loadButton = page.getByRole('button', { name: 'Load worker record' });
  await loadButton.click();
  await firstRequestSeen;
  await page.locator('#people-api-person').fill('person-latest');
  await loadButton.click();

  await expect(page.locator('#people-api-status')).toHaveAttribute('data-state', 'loaded');
  await expect(page.locator('#people-api-display-name')).toHaveText('Latest worker');
  await expect(page.locator('#people-api-employment-status')).toHaveText('active');
  await page.waitForTimeout(250);
  await expect(page.locator('#people-api-display-name')).toHaveText('Latest worker');
  await expect(page.locator('#people-api-employment-status')).toHaveText('active');
});

for (const fixture of [
  {
    name: 'People', view: 'employee-profile', route: '**/v1/tenants/**/people/**',
    input: '#people-api-person', result: '#people-api-result', status: '#people-api-status',
    field: '#people-api-display-name', button: 'Load worker record',
    payload: { fields: { display_name: 'Original worker', employment_status_code: 'active' } },
    fresh: { fields: { display_name: 'Fresh worker', employment_status_code: 'active' } },
    expected: 'Fresh worker',
  },
  {
    name: 'Job Analysis', view: 'job-analysis', route: '**/v1/tenants/**/job-analysis-snapshots/**',
    input: '#job-analysis-record', result: '#job-analysis-result', status: '#job-analysis-status',
    field: '#job-analysis-analysis-id', button: 'Load snapshot',
    payload: jobAnalysisSnapshot,
    fresh: { ...jobAnalysisSnapshot, analysis_record_id: 'analysis-fresh' },
    expected: 'analysis-fresh',
  },
]) {
  test(`${fixture.name} input edits invalidate a pending read and permit a fresh explicit request`, async ({ page }) => {
    await injectProtectedReadConfig(page);
    let markSeen;
    const seen = new Promise((resolve) => { markSeen = resolve; });
    let release;
    const held = new Promise((resolve) => { release = resolve; });
    let requests = 0;
    await page.route(fixture.route, async (route) => {
      requests += 1;
      if (requests === 1) {
        markSeen();
        await held;
      }
      await route.fulfill({ status: 200, contentType: 'application/json',
        body: JSON.stringify(requests === 1 ? fixture.payload : fixture.fresh) });
    });
    try {
      await page.goto(workspacePath);
      await page.locator(`[data-view-link="${fixture.view}"]`).first().click();
      await page.getByRole('button', { name: fixture.button, exact: true }).click();
      await seen;
      const original = await page.locator(fixture.input).inputValue();
      await page.locator(fixture.input).fill('different-resource');
      await page.locator(fixture.input).fill(original);
      await expect(page.locator(fixture.status)).toHaveAttribute('data-state', 'idle');
      const response = page.waitForResponse((value) => value.url().includes('/v1/tenants/'));
      release();
      await (await response).finished();
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await expect(page.locator(fixture.result)).toBeHidden();
      await expect(page.locator(fixture.field)).toHaveText('unknown');
      await expect(page.locator(fixture.status)).toHaveAttribute('data-state', 'idle');
      await page.locator(fixture.input).fill('fresh-resource');
      await page.getByRole('button', { name: fixture.button, exact: true }).click();
      await expect(page.locator(fixture.field)).toHaveText(fixture.expected);
      await expect(page.locator(fixture.result)).toBeVisible();
      await page.locator(fixture.input).fill('another-resource');
      await expect(page.locator(fixture.result)).toBeHidden();
      await expect(page.locator(fixture.field)).toHaveText('unknown');
      expect(requests).toBe(2);
    } finally {
      release();
    }
  });
}

test('host authority invalidation clears both protected surfaces and permits explicit fresh reads', async ({ page }) => {
  await injectProtectedReadConfig(page);
  let requests = 0;
  await page.route('**/v1/tenants/**/people/**', async (route) => {
    requests += 1;
    await route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ fields: { display_name: 'Authorized fixture worker', employment_status_code: 'active' } }) });
  });
  await page.route('**/v1/tenants/**/job-analysis-snapshots/**', async (route) => {
    requests += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(jobAnalysisSnapshot) });
  });
  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.getByRole('button', { name: 'Load worker record', exact: true }).click();
  await expect(page.locator('#people-api-display-name')).toHaveText('Authorized fixture worker');
  await page.locator('[data-view-link="job-analysis"]').first().click();
  await page.getByRole('button', { name: 'Load snapshot', exact: true }).click();
  await expect(page.locator('#job-analysis-analysis-id')).toHaveText(jobAnalysisSnapshot.analysis_record_id);
  const cleared = await page.evaluate(() => {
    document.dispatchEvent(new Event('orgmetra:authority-invalidated'));
    return ['people-api', 'job-analysis'].map((prefix) => ({
      hidden: document.getElementById(`${prefix}-result`).hidden,
      state: document.getElementById(`${prefix}-status`).dataset.state,
    }));
  });
  expect(cleared).toEqual([{ hidden: true, state: 'idle' }, { hidden: true, state: 'idle' }]);
  for (const id of ['people-api-display-name', 'people-api-employment-status', 'job-analysis-analysis-id', 'job-analysis-state', 'job-analysis-effective', 'job-analysis-recorded']) {
    await expect(page.locator(`#${id}`)).toHaveText('unknown');
  }
  for (const id of ['job-analysis-task-count', 'job-analysis-ksao-count']) await expect(page.locator(`#${id}`)).toHaveText('0');
  expect(requests).toBe(2);
  await page.getByRole('button', { name: 'Load snapshot', exact: true }).click();
  await expect(page.locator('#job-analysis-result')).toBeVisible();
  await page.locator('[data-view-link="employee-profile"]').first().click();
  await page.getByRole('button', { name: 'Load worker record', exact: true }).click();
  await expect(page.locator('#people-api-result')).toBeVisible();
  expect(requests).toBe(4);
});

test('personal-details purpose edits clear prior review states without granting access', async ({ page }) => {
  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();
  const purpose = page.locator('#access-purpose');
  const review = page.locator('[data-action="view-personal-details"]');
  const details = page.locator('#details-panel');
  const denial = page.locator('#permission-panel');
  await review.click();
  await expect(details).toBeVisible();
  await purpose.selectOption('recruiting');
  await expect(details).toBeHidden();
  await expect(denial).toBeHidden();
  await review.click();
  await expect(denial).toBeVisible();
  await expect(details).toBeHidden();
  await purpose.selectOption('hr_operations');
  await expect(denial).toBeHidden();
  await expect(details).toBeHidden();
  await review.click();
  await expect(details).toBeVisible();
  await expect(denial).toBeHidden();
});

test('keyboard users can bypass repeated workspace navigation', async ({ page }) => {
  await page.goto(workspacePath);

  await page.keyboard.press('Tab');
  const skipLink = page.getByRole('link', { name: 'Skip to main content' });
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeVisible();

  await skipLink.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});

test('the bypass control follows the active workspace locale', async ({ page }) => {
  await page.goto(workspacePath);

  const skipLink = page.locator('a.skip-link[href="#main-content"]');
  await expect(skipLink).toHaveAccessibleName('Skip to main content');
  await page.locator('#locale-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ko');
  await expect(skipLink.locator('[lang="ko"]')).toBeVisible();
  await expect(skipLink.locator('[lang="en"]')).toBeHidden();
  await expect(skipLink).toHaveAccessibleName('본문으로 건너뛰기');
});

test('sidebar focus and form-control boundaries retain non-text contrast', async ({ page }) => {
  await page.goto(workspacePath);
  /** Calculate WCAG contrast between the two rendered CSS colors used by this browser assertion. */
  const ratio = (a, b) => {
    /** Convert the fixture's RGB color channels to relative luminance for its contrast assertion. */
    const luminance = (color) => {
      const values = color.match(/[\d.]+/g).slice(0, 3).map(Number).map((v) => v / 255).map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
      return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    };
    const x = luminance(a), y = luminance(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  };
  const brand = page.locator('.brand');
  await brand.focus();
  expect(await brand.evaluate((n) => n.matches(':focus-visible'))).toBe(true);
  const focus = await brand.evaluate((n) => ({ ring: getComputedStyle(n).outlineColor, background: getComputedStyle(n.closest('.sidebar')).backgroundColor }));
  expect(ratio(focus.ring, focus.background)).toBeGreaterThanOrEqual(3);
  for (const selector of ['[data-view-link="employee-profile"]', '[data-view-link="job-analysis"]']) {
    const nav = page.locator(selector).first();
    await nav.focus();
    const colors = await nav.evaluate((n) => ({ ring: getComputedStyle(n).outlineColor, background: getComputedStyle(n.closest('.sidebar')).backgroundColor }));
    expect(ratio(colors.ring, colors.background)).toBeGreaterThanOrEqual(3);
  }
  await page.locator('[data-view-link="employee-profile"]').first().click();
  const fields = page.locator('input, textarea, .select-field');
  for (let i = 0; i < await fields.count(); i += 1) {
    const colors = await fields.nth(i).evaluate((n) => ({ border: getComputedStyle(n).borderTopColor, background: getComputedStyle(n).backgroundColor }));
    expect(ratio(colors.border, colors.background)).toBeGreaterThanOrEqual(3);
  }
  const locale = page.locator('#locale-toggle');
  await page.keyboard.press('Tab');
  await locale.focus();
  expect(await locale.evaluate((n) => n.matches(':focus-visible'))).toBe(true);
  await expect(locale).toHaveCSS('outline-color', 'rgb(29, 78, 137)');
});

for (const [view, prefix, key] of [['employee-profile', 'people-api', 'peopleApiInvalidInput'], ['job-analysis', 'job-analysis', 'jobAnalysisInvalidInput']]) {
  test(`${prefix} rejects empty and whitespace purpose before issuing credentials`, async ({ page }) => {
    await page.addInitScript(() => {
      window.__issued = 0;
      /** Count synthetic credential requests so blank-purpose rejection proves pre-issuance ordering. */
      const getAuthorization = () => { window.__issued += 1; return 'Bearer synthetic-purpose-only'; };
      window.__ORGMETRA_PEOPLE__ = { baseUrl: location.origin, tenantRecordId: 'tenant', personRecordId: 'person', effectiveOn: '2026-11-10', getAuthorization };
      window.__ORGMETRA_JOB_ANALYSIS__ = { baseUrl: location.origin, tenantRecordId: 'tenant', analysisRecordId: 'analysis', getAuthorization };
    });
    let sends = 0;
    const purposes = [];
    await page.route('**/v1/**', async (route) => {
      sends += 1;
      purposes.push(prefix === 'people-api' ? new URL(route.request().url()).searchParams.get('purpose') : (await route.request().allHeaders())['x-purpose-code']);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(prefix === 'people-api' ? { fields: { display_name: 'Purpose fixture', employment_status_code: 'active' } } : jobAnalysisSnapshot) });
    });
    await page.goto(workspacePath);
    await page.locator(`[data-view-link="${view}"]`).first().click();
    const purpose = page.locator(`#${prefix}-purpose`);
    const submit = page.locator(`#${prefix}-form button[type="submit"]`);
    await submit.click();
    await expect(page.locator(`#${prefix}-result`)).toBeVisible();
    expect(await page.evaluate(() => window.__issued)).toBe(1);
    expect(sends).toBe(1);
    for (const value of ['', '   ']) {
      await purpose.fill(value);
      await submit.click();
      await expect(page.locator(`#${prefix}-status`)).toHaveAttribute('data-i18n', key);
      await expect(page.locator(`#${prefix}-status`)).toHaveAttribute('data-state', 'error');
      await expect(page.locator(`#${prefix}-result`)).toBeHidden();
      expect(await page.evaluate(() => window.__issued)).toBe(1);
      expect(sends).toBe(1);
    }
    await page.locator('#locale-toggle').click();
    await expect(page.locator(`#${prefix}-status`)).toContainText('확인');
    await purpose.fill('specific_review');
    await submit.click();
    await expect(page.locator(`#${prefix}-status`)).toHaveAttribute('data-state', 'loaded');
    await expect(page.locator(`#${prefix}-result`)).toBeVisible();
    expect(await page.evaluate(() => window.__issued)).toBe(2);
    expect(sends).toBe(2);
    expect(purposes).toEqual([prefix === 'people-api' ? 'people_read' : 'job_analysis_read', 'specific_review']);
  });
}

test('invalid protected-read forms issue no credentials or requests and explain local input', async ({ page }) => {
  await page.addInitScript(() => {
    window.__issued = 0;
    /** Return the synthetic test credential; the validation-order fixture also counts requests for it. */
    const getAuthorization = () => { window.__issued += 1; return 'Bearer synthetic-only'; };
    window.__ORGMETRA_PEOPLE__ = { baseUrl: location.origin, tenantRecordId: 'tenant', personRecordId: 'person', effectiveOn: '2026-11-10', getAuthorization };
    window.__ORGMETRA_JOB_ANALYSIS__ = { baseUrl: location.origin, tenantRecordId: 'tenant', analysisRecordId: 'analysis', getAuthorization };
  });
  let sends = 0;
  await page.route('**/v1/**', (route) => { sends += 1; return route.fulfill({ status: 500, body: '{}' }); });
  await page.goto(workspacePath);
  for (const [view, prefix, key] of [['employee-profile', 'people-api', 'peopleApiInvalidInput'], ['job-analysis', 'job-analysis', 'jobAnalysisInvalidInput']]) {
    await page.locator(`[data-view-link="${view}"]`).first().click();
    await page.locator(`#${prefix}-tenant`).fill('');
    await page.locator(`#${prefix}-form button[type="submit"]`).click();
    await expect(page.locator(`#${prefix}-status`)).toHaveAttribute('data-i18n', key);
    await expect(page.locator(`#${prefix}-status`)).toContainText('Check');
    await page.locator('#locale-toggle').click();
    await expect(page.locator(`#${prefix}-status`)).toContainText('확인');
    await page.locator('#locale-toggle').click();
    await expect(page.locator(`#${prefix}-result`)).toBeHidden();
  }
  expect(await page.evaluate(() => window.__issued)).toBe(0);
  expect(sends).toBe(0);
});
