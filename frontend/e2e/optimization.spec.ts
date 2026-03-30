import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Optimization workflow', () => {
  test('run optimization shows chart and results table', async ({ page }) => {
    const results = [
      { time: '2026-03-26T10:00:00', battery_id: 'bat-1', charge: 5.0, discharge: 0, soc: 25.0, grid_buy: 10.0, grid_sell: 0 },
      { time: '2026-03-26T11:00:00', battery_id: 'bat-1', charge: 0, discharge: 3.0, soc: 22.0, grid_buy: 0, grid_sell: 5.0 },
      { time: '2026-03-26T12:00:00', battery_id: 'bat-1', charge: 2.0, discharge: 0, soc: 24.0, grid_buy: 2.0, grid_sell: 0 },
    ];

    await page.route(`${API}/optimize`, async (route) => {
      await route.fulfill({
        status: 200, contentType: 'application/json', body: JSON.stringify(results),
      });
    });

    await page.goto('/optimization');
    await page.getByRole('button', { name: /Run Optimization/i }).click();

    // Chart.js renders canvas
    await expect(page.locator('canvas')).toBeVisible();

    // Results table should show battery data
    await expect(page.getByText('bat-1').first()).toBeVisible();
  });

  test('optimization error shows error message', async ({ page }) => {
    await page.route(`${API}/optimize`, async (route) => {
      await route.fulfill({
        status: 500, contentType: 'application/json',
        body: JSON.stringify({ detail: 'No batteries configured' }),
      });
    });

    await page.goto('/optimization');
    await page.getByRole('button', { name: /Run Optimization/i }).click();

    await expect(page.getByText(/No batteries configured|error|failed/i)).toBeVisible();
  });

  test('empty optimization shows no chart', async ({ page }) => {
    await page.route(`${API}/optimize`, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/optimization');
    await page.getByRole('button', { name: /Run Optimization/i }).click();

    // No canvas should appear with empty results
    await page.waitForTimeout(500);
    await expect(page.locator('canvas')).not.toBeVisible();
  });
});
