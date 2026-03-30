import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Sidebar action buttons', () => {
  test('Init DB button opens progress dialog', async ({ page }) => {
    await page.route(`${API}/admin/init-db-stream`, async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: [
          'data: {"step":"Creating database tables","status":"done","count":0}\n\n',
          'data: {"step":"Seeding load data","status":"done","count":100}\n\n',
          'data: {"step":"Seeding market data","status":"done","count":100}\n\n',
          'data: {"step":"complete","status":"done"}\n\n',
        ].join(''),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Init DB', exact: true }).click();

    await expect(page.getByText('Initialize Database')).toBeVisible();
    await expect(page.getByText('Database initialized successfully.')).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByText('Initialize Database')).not.toBeVisible();
  });

  test('Reset & Init DB shows confirmation dialog', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Reset & Init DB' }).click();

    await expect(page.getByText('wipe all data')).toBeVisible();

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByText('wipe all data')).not.toBeVisible();
  });

  test('Train Model button shows loading state', async ({ page }) => {
    await page.route(`${API}/forecasting/train`, async (route) => {
      await new Promise((r) => setTimeout(r, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Training started',
          status: { is_training: false, last_training: null, is_running_inference: false, last_inference: null },
        }),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Train Model' }).click();
    await expect(page.getByText('Training…')).toBeVisible();
  });

  test('Run Inference button shows loading state', async ({ page }) => {
    await page.route(`${API}/forecasting/inference`, async (route) => {
      await new Promise((r) => setTimeout(r, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Inference started',
          status: { is_training: false, last_training: null, is_running_inference: false, last_inference: null },
        }),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Run Inference' }).click();
    await expect(page.getByText('Running…')).toBeVisible();
  });
});
