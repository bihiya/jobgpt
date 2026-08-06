import { expect, test } from '@playwright/test';

test('login page renders brand and form', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('JobPilot AI')).toBeVisible();
  await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  await expect(page.getByLabel(/email/i)).toBeVisible();
});
