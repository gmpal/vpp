import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Sidebar navigation', () => {
  test('loads the map page by default', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'VPP Manager' })).toBeVisible();
    const mapLink = page.getByRole('link', { name: 'Map', exact: true });
    await expect(mapLink).toBeVisible();
  });

  const routes = [
    { label: 'Community', path: '/community' },
    { label: 'Households', path: '/households' },
    { label: 'Vehicles', path: '/vehicles' },
    { label: 'Grid', path: '/grid' },
    { label: 'Profiles', path: '/profiles' },
    { label: 'Forecast', path: '/forecast' },
  ];

  for (const { label, path } of routes) {
    test(`navigates to ${label} page`, async ({ page }) => {
      await page.goto('/');
      await page.getByRole('link', { name: label }).click();
      await expect(page).toHaveURL(path);
    });
  }
});
