import { expect, test } from '@playwright/test';

const workspacePath = '/apps/hr-workspace/index.html';

test('employee profile keeps Job, Position, and Assignment as distinct HRIS concepts', async ({ page }) => {
  await page.goto(workspacePath);
  await page.locator('[data-view-link="employee-profile"]').first().click();

  const conceptGrid = page.locator('#view-employee-profile .concept-grid');
  await expect(conceptGrid.locator('.concept-card')).toHaveCount(5);

  const jobCard = conceptGrid.locator('.concept-card', { hasText: 'job_record' });
  const positionCard = conceptGrid.locator('.concept-card', { hasText: 'position_record' });
  const assignmentCard = conceptGrid.locator('.concept-card', { hasText: 'assignment_record' });

  await expect(jobCard).toHaveCount(1);
  await expect(positionCard).toHaveCount(1);
  await expect(assignmentCard).toHaveCount(1);
  await expect(jobCard.locator('strong')).toHaveText('job_record');
  await expect(positionCard.locator('strong')).toHaveText('position_record');
  await expect(assignmentCard.locator('strong')).toHaveText('assignment_record');

  await page.locator('#locale-toggle').click();
  await expect(jobCard).toContainText('직무');
  await expect(positionCard).toContainText('직위');
  await expect(assignmentCard).toContainText('배정');
});
