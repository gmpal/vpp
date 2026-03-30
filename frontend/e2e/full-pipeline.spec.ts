import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

/**
 * Tests full user journeys across multiple pages.
 * All API calls are mocked to simulate the full pipeline without real infrastructure.
 */
test.describe('Full pipeline user journey', () => {
  test('init db → train → infer → view forecast', async ({ page }) => {
    await mockAllApis(page);

    let dbInitialized = false;
    let trained = false;
    let inferenceRun = false;

    await page.route(`${API}/admin/init-db-stream`, async (route) => {
      dbInitialized = true;
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: [
          'data: {"step":"Creating database tables","status":"done","count":0}\n\n',
          'data: {"step":"Seeding load data","status":"done","count":500}\n\n',
          'data: {"step":"Seeding market data","status":"done","count":500}\n\n',
          'data: {"step":"complete","status":"done"}\n\n',
        ].join(''),
      });
    });

    await page.route(`${API}/forecasting/train`, async (route) => {
      trained = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Training completed',
          status: { is_training: false, last_training: '2026-03-26T12:00:00Z', is_running_inference: false, last_inference: null },
        }),
      });
    });

    await page.route(`${API}/forecasting/inference`, async (route) => {
      inferenceRun = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Inference completed',
          status: { is_training: false, last_training: '2026-03-26T12:00:00Z', is_running_inference: false, last_inference: '2026-03-26T12:05:00Z' },
        }),
      });
    });

    await page.route(`${API}/source-ids/solar`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(['src-001']) })
    );

    await page.route(`${API}/forecasted/solar*`, (route) => {
      if (!inferenceRun) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { timestamp: '2026-03-26T13:00:00Z', value: 4.2 },
          { timestamp: '2026-03-26T14:00:00Z', value: 3.8 },
          { timestamp: '2026-03-26T15:00:00Z', value: 2.5 },
        ]),
      });
    });

    // Step 1: Initialize database
    await page.goto('/');
    await page.getByRole('button', { name: 'Init DB', exact: true }).click();
    await expect(page.getByText('Database initialized successfully.')).toBeVisible({ timeout: 10000 });
    await page.getByRole('button', { name: 'Close' }).click();
    expect(dbInitialized).toBe(true);

    // Step 2: Train model
    await page.getByRole('button', { name: 'Train Model' }).click();
    await expect(page.getByRole('button', { name: 'Train Model' })).toBeEnabled({ timeout: 10000 });
    expect(trained).toBe(true);

    // Step 3: Run inference
    await page.getByRole('button', { name: 'Run Inference' }).click();
    await expect(page.getByRole('button', { name: 'Run Inference' })).toBeEnabled({ timeout: 10000 });
    expect(inferenceRun).toBe(true);

    // Step 4: Navigate to forecast and verify chart
    await page.getByRole('link', { name: 'Forecast' }).click();
    await expect(page).toHaveURL('/forecast');
    await expect(page.locator('.recharts-responsive-container')).toBeVisible({ timeout: 10000 });
  });

  test('add household → navigate to vehicles → see EVs', async ({ page }) => {
    await mockAllApis(page);

    let householdCreated = false;

    await page.route(`${API}/households`, async (route) => {
      if (route.request().method() === 'POST') {
        householdCreated = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            household_id: 'hh-new', name: 'My House', latitude: 50.85, longitude: 4.35,
            solar_panels: 4, building_type: 'household', num_people: 3, num_evs: 1,
          }),
        });
      }
      const list = householdCreated
        ? [{ household_id: 'hh-new', name: 'My House', latitude: 50.85, longitude: 4.35,
             solar_panels: 4, building_type: 'household', num_people: 3, num_evs: 1 }]
        : [];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) });
    });

    await page.route(`${API}/vehicles`, async (route) => {
      const list = householdCreated
        ? [{ vehicle_id: 'ev-new', household_id: 'hh-new', name: 'My House EV 1',
             capacity_kwh: 60, soc_kwh: 30, max_charge_kw: 7.4, max_discharge_kw: 7.4,
             eta: 0.9, status: 'home' }]
        : [];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) });
    });

    await page.goto('/households');
    await expect(page.getByText('No households yet')).toBeVisible();

    // Add household
    await page.getByRole('button', { name: 'Add Household' }).click();
    const nameField = page.getByLabel('Name');
    await nameField.clear();
    await nameField.fill('My House');
    await page.getByRole('button', { name: 'Add' }).click();
    await expect(page.getByText('My House').first()).toBeVisible();

    // Navigate to vehicles
    await page.getByRole('link', { name: 'Vehicles' }).click();
    await expect(page).toHaveURL('/vehicles');

    await expect(page.getByText('My House').first()).toBeVisible();
    await expect(page.getByText('My House EV 1')).toBeVisible();
    await expect(page.getByText('30.0/60 kWh (50%)')).toBeVisible();
  });
});
