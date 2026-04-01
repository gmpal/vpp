import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Page rendering', () => {
  test('Community page renders', async ({ page }) => {
    await page.goto('/community');
    await expect(page.getByRole('heading', { name: 'Community Dashboard' })).toBeVisible();
  });

  test('Households page renders', async ({ page }) => {
    await page.goto('/households');
    await expect(page.getByRole('heading', { name: /household/i })).toBeVisible();
  });

  test('Vehicles page renders', async ({ page }) => {
    await page.goto('/vehicles');
    await expect(page.getByRole('heading', { name: 'Vehicles', exact: true })).toBeVisible();
  });

  test('Grid page renders', async ({ page }) => {
    await page.goto('/grid');
    await expect(page.locator('main').getByRole('heading', { name: 'Grid' })).toBeVisible();
  });

  test('Profiles page renders', async ({ page }) => {
    await page.goto('/profiles');
    await expect(page.getByRole('heading', { name: /profile/i })).toBeVisible();
  });

  test('Forecast page renders', async ({ page }) => {
    await page.goto('/forecast');
    await expect(page.getByRole('heading', { name: 'Forecast Viewer' })).toBeVisible();
  });
});
