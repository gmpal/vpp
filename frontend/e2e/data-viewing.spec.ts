import { test, expect } from '@playwright/test';
import { mockAllApis } from './fixtures';

const API = 'http://localhost:8000/api';

const SOLAR_DATA = [
  { timestamp: '2026-03-26T10:00:00Z', value: 3.2 },
  { timestamp: '2026-03-26T11:00:00Z', value: 5.1 },
  { timestamp: '2026-03-26T12:00:00Z', value: 4.8 },
];

const LOAD_DATA = [
  { timestamp: '2026-03-26T10:00:00Z', value: 2.5 },
  { timestamp: '2026-03-26T11:00:00Z', value: 3.0 },
  { timestamp: '2026-03-26T12:00:00Z', value: 2.8 },
];

const MARKET_DATA = [
  { timestamp: '2026-03-26T10:00:00Z', value: 45.2 },
  { timestamp: '2026-03-26T11:00:00Z', value: 42.0 },
  { timestamp: '2026-03-26T12:00:00Z', value: 48.5 },
];

const FORECAST_DATA = [
  { timestamp: '2026-03-26T13:00:00Z', value: 4.0 },
  { timestamp: '2026-03-26T14:00:00Z', value: 3.5 },
  { timestamp: '2026-03-26T15:00:00Z', value: 2.1 },
];

// Recharts renders SVG charts, not canvas
const RECHARTS = '.recharts-responsive-container';

test.beforeEach(async ({ page }) => {
  await mockAllApis(page);
});

test.describe('Grid page', () => {
  test('displays load and market charts', async ({ page }) => {
    await page.route(`${API}/historical/load*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LOAD_DATA) })
    );
    await page.route(`${API}/historical/market*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MARKET_DATA) })
    );

    await page.goto('/grid');

    const charts = page.locator(RECHARTS);
    await expect(charts.first()).toBeVisible();
    await expect(charts).toHaveCount(2);
  });
});

test.describe('Profiles page', () => {
  test('displays three profile charts (solar, load, market)', async ({ page }) => {
    await page.route(`${API}/source-ids/solar`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(['src-001']) })
    );
    await page.route(`${API}/historical/solar*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SOLAR_DATA) })
    );
    await page.route(`${API}/historical/load*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LOAD_DATA) })
    );
    await page.route(`${API}/historical/market*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MARKET_DATA) })
    );

    await page.goto('/profiles');

    const charts = page.locator(RECHARTS);
    await expect(charts.first()).toBeVisible();
    await expect(charts).toHaveCount(3);
  });

  test('shows error when backend is unavailable', async ({ page }) => {
    await page.route(`${API}/source-ids/**`, (route) => route.abort('connectionrefused'));
    await page.route(`${API}/historical/**`, (route) => route.abort('connectionrefused'));

    await page.goto('/profiles');
    await expect(page.getByText(/could not load|error|backend/i)).toBeVisible();
  });
});

test.describe('Forecast page', () => {
  test('shows forecast chart when data exists', async ({ page }) => {
    await page.route(`${API}/source-ids/solar`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(['src-001']) })
    );
    await page.route(`${API}/forecasted/solar*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FORECAST_DATA) })
    );

    await page.goto('/forecast');
    await expect(page.locator(RECHARTS)).toBeVisible();
  });

  test('shows empty message when no forecast data', async ({ page }) => {
    await page.goto('/forecast');
    await expect(page.getByText(/No forecast data available/i)).toBeVisible();
  });

  test('switching source type to Load fetches load forecasts', async ({ page }) => {
    await page.route(`${API}/forecasted/load*`, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FORECAST_DATA) })
    );

    await page.goto('/forecast');
    await page.getByLabel('Source Type').click();
    await page.getByRole('option', { name: /Load/i }).click();

    await expect(page.locator(RECHARTS)).toBeVisible();
  });
});
