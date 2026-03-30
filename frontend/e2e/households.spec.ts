import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Household management', () => {
  test('shows empty state when no households exist', async ({ page }) => {
    await page.goto('/households');
    await expect(page.getByText('No households yet')).toBeVisible();
  });

  test('add household via dialog', async ({ page }) => {
    let createCalled = false;
    await page.route(`${API}/households`, async (route) => {
      if (route.request().method() === 'POST') {
        createCalled = true;
        const body = JSON.parse(route.request().postData() || '{}');
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            household_id: 'hh-001', name: body.name || 'New Household',
            latitude: body.latitude, longitude: body.longitude,
            solar_panels: 0, building_type: 'household', num_people: 1, num_evs: 0,
          }),
        });
      }
      // GET: return household after creation
      const list = createCalled
        ? [{ household_id: 'hh-001', name: 'Test House', latitude: 50.85, longitude: 4.35,
             solar_panels: 4, building_type: 'household', num_people: 3, num_evs: 0 }]
        : [];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) });
    });

    await page.goto('/households');
    await page.getByRole('button', { name: 'Add Household' }).click();

    const nameField = page.getByLabel('Name');
    await nameField.clear();
    await nameField.fill('Test House');
    await page.getByRole('button', { name: 'Add' }).click();

    await expect(page.getByText('Test House', { exact: true }).first()).toBeVisible();
  });

  test('cancel add household closes dialog without creating', async ({ page }) => {
    await page.goto('/households');
    await page.getByRole('button', { name: 'Add Household' }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('delete household removes it from list', async ({ page }) => {
    let deleted = false;
    await page.route(`${API}/households`, async (route) => {
      const list = deleted ? [] : [{
        household_id: 'hh-001', name: 'To Delete', latitude: 50.85, longitude: 4.35,
        solar_panels: 0, building_type: 'household', num_people: 1, num_evs: 0,
      }];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) });
    });
    await page.route(`${API}/households/hh-001`, async (route) => {
      deleted = true;
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/households');
    await expect(page.getByText('To Delete')).toBeVisible();

    await page.locator('main [data-testid="DeleteIcon"]').first().click();
    await expect(page.getByText('To Delete')).not.toBeVisible();
  });

  test('add EV to a household', async ({ page }) => {
    let vehicleCreated = false;
    await page.route(`${API}/households`, async (route) => {
      return route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([{
          household_id: 'hh-001', name: 'My House', latitude: 50.85, longitude: 4.35,
          solar_panels: 4, building_type: 'household', num_people: 3, num_evs: 0,
        }]),
      });
    });
    await page.route(`${API}/vehicles`, async (route) => {
      if (route.request().method() === 'POST') {
        vehicleCreated = true;
        const body = JSON.parse(route.request().postData() || '{}');
        return route.fulfill({
          status: 200, contentType: 'application/json',
          body: JSON.stringify({
            vehicle_id: 'ev-001', household_id: body.household_id, name: body.name,
            capacity_kwh: body.capacity_kwh, soc_kwh: body.soc_kwh,
            max_charge_kw: body.max_charge_kw, max_discharge_kw: body.max_discharge_kw,
            eta: body.eta ?? 0.9, status: 'home',
          }),
        });
      }
      const list = vehicleCreated
        ? [{ vehicle_id: 'ev-001', household_id: 'hh-001', name: 'Family EV',
             capacity_kwh: 75, soc_kwh: 37.5, max_charge_kw: 11, max_discharge_kw: 7,
             eta: 0.9, status: 'home' }]
        : [];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) });
    });

    await page.goto('/households');
    await expect(page.getByText('My House')).toBeVisible();

    await page.getByRole('button', { name: 'Add EV' }).click();
    // Native select — use selectOption
    await page.getByLabel('Household').selectOption({ label: 'My House' });

    const nameField = page.getByLabel('Name');
    await nameField.clear();
    await nameField.fill('Family EV');
    await page.getByRole('button', { name: 'Add' }).click();

    await expect(page.getByText('Family EV')).toBeVisible();
  });
});
