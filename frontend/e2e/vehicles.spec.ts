import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

const HOUSEHOLD = {
  household_id: 'hh-001', name: 'Test House', latitude: 50.85, longitude: 4.35,
  solar_panels: 4, building_type: 'household', num_people: 3, num_evs: 1,
};

function makeVehicle(overrides: Record<string, any> = {}) {
  return {
    vehicle_id: 'ev-001', household_id: 'hh-001', name: 'Test EV',
    capacity_kwh: 60, soc_kwh: 30, max_charge_kw: 7.4, max_discharge_kw: 7.4,
    eta: 0.9, status: 'home', ...overrides,
  };
}

function setupVehicleRoutes(page: any, household: any, vehicle: any) {
  return Promise.all([
    page.route(`${API}/households`, (route: any) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([household]) })
    ),
    page.route(`${API}/vehicles`, (route: any) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([vehicle]) })
    ),
  ]);
}

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Vehicle panel', () => {
  test('shows empty state when no vehicles exist', async ({ page }) => {
    await page.goto('/vehicles');
    await expect(page.getByText('No vehicles yet')).toBeVisible();
  });

  test('displays vehicles grouped by household with SOC', async ({ page }) => {
    await setupVehicleRoutes(page, HOUSEHOLD, makeVehicle());

    await page.goto('/vehicles');
    await expect(page.getByText('Test House')).toBeVisible();
    await expect(page.getByText('Test EV')).toBeVisible();
    await expect(page.getByText('30.0/60 kWh (50%)')).toBeVisible();
  });

  test('charge vehicle updates SOC', async ({ page }) => {
    let currentSoc = 30;
    await page.route(`${API}/households`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([HOUSEHOLD]) })
    );
    await page.route(`${API}/vehicles`, (route) =>
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([makeVehicle({ soc_kwh: currentSoc })]),
      })
    );
    await page.route(`${API}/vehicles/ev-001/charge`, async (route) => {
      currentSoc = 37.4;
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(makeVehicle({ soc_kwh: currentSoc })),
      });
    });

    await page.goto('/vehicles');
    await expect(page.getByText('30.0/60 kWh (50%)')).toBeVisible();

    // Expand the EV card
    await page.locator('[data-testid="ExpandMoreIcon"]').first().click();

    // Click Charge button (text like "Charge 3.7 kW")
    await page.getByRole('button', { name: /^Charge \d/ }).click();

    // SOC should update
    await expect(page.getByText(/37\.4\/60 kWh/)).toBeVisible();
  });

  test('discharge vehicle updates SOC', async ({ page }) => {
    let currentSoc = 30;
    await page.route(`${API}/households`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([HOUSEHOLD]) })
    );
    await page.route(`${API}/vehicles`, (route) =>
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([makeVehicle({ soc_kwh: currentSoc })]),
      })
    );
    await page.route(`${API}/vehicles/ev-001/discharge`, async (route) => {
      currentSoc = 22.6;
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify(makeVehicle({ soc_kwh: currentSoc })),
      });
    });

    await page.goto('/vehicles');
    await page.locator('[data-testid="ExpandMoreIcon"]').first().click();
    await page.getByRole('button', { name: 'Discharge' }).click();

    await expect(page.getByText(/22\.6\/60 kWh/)).toBeVisible();
  });

  test('fully charged vehicle disables charge button', async ({ page }) => {
    await setupVehicleRoutes(page, HOUSEHOLD, makeVehicle({ soc_kwh: 60 }));

    await page.goto('/vehicles');
    // 100% SOC shown
    await expect(page.getByText('60.0/60 kWh (100%)')).toBeVisible();

    await page.locator('[data-testid="ExpandMoreIcon"]').first().click();

    // Charge button should be disabled
    const chargeBtn = page.getByRole('button', { name: /^Charge \d/ });
    await expect(chargeBtn).toBeDisabled();
  });
});
