# VPP Frontend

React + TypeScript frontend for the Virtual Power Plant simulation.

## Stack

- **React 19** with TypeScript
- **Material-UI (MUI) 6** — component library
- **React Router 7** — client-side routing
- **Axios** — API client (`src/api.ts`)
- **Chart.js / Recharts** — data visualisation
- **Leaflet / MapLibre GL** — interactive map
- **Playwright** — E2E tests

## Scripts

```bash
npm start          # dev server at http://localhost:3000
npm run build      # production build (TypeScript compile + bundle)
npm test           # jest unit tests (watch mode)
npm run test:e2e          # Playwright E2E (headless)
npm run test:e2e:headed   # Playwright E2E (visible browser)
npm run test:e2e:ui       # Playwright interactive UI
```

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/login` | `LoginPage` | Auth — public |
| `/` | `Map3D` | Interactive VPP map (default view) |
| `/community` | `CommunityDashboard` | Household aggregation |
| `/households` | `HouseholdPanel` | Manage households + EVs |
| `/vehicles` | `VehiclePanel` | EV charge/discharge status |
| `/renewables` | `Renewables` | Solar/wind historical + forecast |
| `/grid` | `Grid` | Grid import/export charts |
| `/market` | `Market` | Market price data |
| `/optimization` | `Optimization` | Run dispatch optimization |
| `/profiles` | `ProfilesTab` | Per-household load profiles |
| `/forecast` | `ForecastTab` | Unified forecast viewer |

All routes except `/login` are wrapped in `ProtectedRoute` — redirect to `/login` if unauthenticated.

## Project Structure

```
src/
├── api.ts                  # Axios instance + all API calls
├── App.tsx                 # Router + layout shell
├── index.tsx               # React entry point
├── chartjs-config.tsx      # Chart.js global registration
├── types.tsx               # Shared TypeScript interfaces
│
├── components/             # Reusable UI components
│   ├── Sidebar.tsx         # Navigation sidebar
│   ├── Map3D.tsx           # Interactive Leaflet/MapLibre map
│   ├── ProtectedRoute.tsx  # Auth guard
│   ├── CommunityDashboard.tsx
│   ├── HouseholdPanel.tsx
│   ├── VehiclePanel.tsx
│   ├── EVCard.tsx
│   ├── TimelineBar.tsx
│   ├── ProfilesTab.tsx
│   └── ForecastTab.tsx
│
├── pages/
│   └── LoginPage.tsx       # Login form
│
├── context/
│   └── AuthContext.tsx     # JWT auth state (login/logout/token)
│
└── utils/
    ├── geoUtils.ts         # Coordinate helpers for map
    └── naiveForecast.ts    # Client-side naive forecast baseline
```

## API Client

All backend calls go through `src/api.ts`. It exports typed functions for each endpoint and attaches the JWT token from `AuthContext` automatically. The base URL is controlled by `REACT_APP_API_BASE_URL` (must include `/api` suffix).

## Adding a New Page

1. Create `src/components/MyPage.tsx`
2. Import and add a `<Route>` in `App.tsx`:
   ```tsx
   <Route path="/my-page" element={<ProtectedRoute><MyPage /></ProtectedRoute>} />
   ```
3. Add a nav entry in `src/components/Sidebar.tsx`
4. Add API mock in `frontend/e2e/fixtures.ts` for E2E coverage

## E2E Tests

Tests live in `frontend/e2e/` and mock all API calls — **no running backend needed**.

```
e2e/
├── fixtures.ts             # Shared mock setup — import mockAllApis() in new tests
├── navigation.spec.ts      # Sidebar nav to all routes
├── pages.spec.ts           # Each page renders its heading
├── sidebar-actions.spec.ts # Init DB, Reset, Train, Inference states
├── households.spec.ts      # Add/delete households, add EVs
├── vehicles.spec.ts        # Charge/discharge SOC, disabled states
├── optimization.spec.ts    # Run optimization, chart/table, errors
├── data-viewing.spec.ts    # Renewables, Grid, Profiles, Forecast viewer
└── full-pipeline.spec.ts   # Multi-page journeys
```

When adding a new API endpoint, add its mock to `fixtures.ts` so existing tests don't break.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `REACT_APP_API_BASE_URL` | Backend base URL — must include `/api` (e.g. `http://localhost:8000/api`) |
