import { expect, test } from '@playwright/test';

const workspacePath = '/apps/hr-workspace/index.html';

async function injectProtectedReadConfig(page) {
  await page.addInitScript(() => {
    const baseUrl = window.location.origin;
    const getAuthorization = () => 'Bearer e2e-host-token';
    window.__ORGMETRA_JOB_ANALYSIS__ = {
      baseUrl,
      tenantRecordId: 'tenant-e2e',
      analysisRecordId: 'analysis-e2e',
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
  });
}

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
      body: JSON.stringify({
        analysis_record_id: 'analysis-e2e',
        status_code: 'analysis_validated',
        effective_from: '2026-08-01',
        recorded_at: '2026-08-18T05:00:00Z',
        content_digest_sha256: 'a'.repeat(64),
        tasks: [{ task_id: 'task-e2e' }],
        ksao_requirements: [{ ksao_id: 'ksao-e2e' }],
      }),
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
  await expect(page.locator('#job-analysis-task-count')).toHaveText('1');
  await expect(page.locator('#job-analysis-ksao-count')).toHaveText('1');

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
