import { Page, Route } from '@playwright/test';

const API = 'http://localhost:8000/api';

const FAKE_USER = { user_id: 'usr_test123', username: 'testuser' };
const FAKE_TOKEN = 'fake-jwt-token-for-e2e-tests';

/**
 * Mock all backend API endpoints so E2E tests can run without a live backend.
 *
 * Playwright evaluates routes in LIFO order (last registered wins).
 * Tests that need custom responses should register their overrides AFTER calling mockAllApis.
 *
 * For paths that collide with frontend routes (e.g. /vehicles), we use
 * the full API URL to avoid intercepting page navigation.
 */
export async function mockAllApis(page: Page) {
  // Auth: mock /auth/me so ProtectedRoute sees a valid session
  await page.route(`${API}/auth/me`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_USER) })
  );
  await page.route(`${API}/auth/token`, (route) =>
    route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ access_token: FAKE_TOKEN, token_type: 'bearer' }),
    })
  );
  await page.route(`${API}/auth/register`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_USER) })
  );

  // Set token in localStorage so ProtectedRoute doesn't redirect to /login
  await page.addInitScript((token) => {
    localStorage.setItem('vpp_token', token);
  }, FAKE_TOKEN);

  // Ambiguous paths (collide with frontend routes) — use exact API URL
  await page.route(`${API}/sources`, emptyArray);
  await page.route(`${API}/sources/*`, emptyObj);
  await page.route(`${API}/households`, emptyArray);
  await page.route(`${API}/households/*`, emptyObj);
  await page.route(`${API}/vehicles`, emptyArray);
  await page.route(`${API}/vehicles/*`, emptyObj);
  await page.route(`${API}/batteries`, emptyArray);

  // Unique API paths — safe to use full URL patterns
  await page.route(`${API}/community/summary`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_households: 0, total_evs: 0, total_solar_panels: 0, total_batteries: 0,
        total_production: 0, total_consumption: 0, net: 0, action: 'self_sufficient',
      }),
    })
  );
  await page.route(`${API}/device-status`, jsonReply({ solar: 0, wind: 0 }));
  await page.route(`${API}/source-ids/*`, emptyArray);
  await page.route(`${API}/realtime-data/*`, emptyArray);
  await page.route(`${API}/historical/*`, emptyArray);
  await page.route(`${API}/forecasted/*`, emptyArray);
  await page.route(`${API}/forecasting/status`, jsonReply({
    last_training: null, is_training: false, last_inference: null, is_running_inference: false,
  }));
  await page.route(`${API}/weather/*`, emptyObj);
  await page.route(`${API}/optimize`, emptyArray);
}

// Helpers
function emptyArray(route: Route) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
}

function emptyObj(route: Route) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
}

function jsonReply(data: any) {
  return (route: Route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) });
}
