import { expect, test } from '@playwright/test';

const workspacePath = '/apps/hr-workspace/index.html';

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

  const skipLink = page.getByRole('link', { name: 'Skip to main content' });
  await page.locator('#locale-toggle').click();
  await expect(skipLink).toHaveText('본문으로 건너뛰기');
  await expect(skipLink).toHaveAccessibleName('본문으로 건너뛰기');
});
