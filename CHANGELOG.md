# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Frontend CI workflow — `npm run build` + Playwright E2E on every PR
- Docker build verification in Backend CI
- PR template (`.github/pull_request_template.md`)
- Ruff linting replacing Flake8 (`pyproject.toml`)
- Pre-commit hooks: ruff, ruff-format, prettier, file hygiene checks
- Mermaid architecture diagram in README
- `CONTRIBUTING.md` with branch conventions and coding standards
- Inline documentation in `.env.example`
- API console (`tools/api-console/index.html`, `make console`) — static page with buttons and plots for manually exercising every backend route; backend URL via `?api=`
- Optimization sell price: energy sold earns the market price × `OPTIMIZATION_SELL_PRICE_FACTOR` (default 0.3), overridable per request with `POST /api/optimize?sell_price_factor=`
- Optimization values energy left in EVs at the window's average buy price, so cheap surplus is stored rather than sold

### Changed
- `POST /api/optimize` plans a 24 h hourly UTC window from the current hour. Inputs use forecasts first, then history at the same hours, then an hour-of-day profile from the 7 days of history closest to the window — no trained models needed. Missing load or market data returns 400 instead of 500
- Optimization result rows add `solar`, `load`, `price`, `sell_price`, `stored_energy_price`, `stored_energy_value` and `objective`; `total_cost` is the net grid cost
- `top` on `/api/historical` and `/api/realtime-data` keeps the most recent points when no `start`/`since` is given (rows still oldest first); with `start` it keeps the first points from there. Frontend charts that pass `top` (Market, Grid, Profiles, Community dashboard) now show recent data instead of the oldest stored
- `/api/realtime-data?since=` returns only points strictly after `since` (was inclusive, re-sending the last point on every poll)
- `POST /api/data/generate-system-data` regenerates market prices (replacing existing rows) and rebuilds load from households; it no longer writes synthetic load. Response adds `market_points` and `load_points`
- Time-series writes are batched (`CrudManager.save_series`, forecasts, household load): seeding 2,400 market rows takes 0.16 s instead of ~63 s
- `electric_vehicles.max_discharge_kw` may be 0 (charge-only EVs); idempotent migration runs on init-db and API startup
- Stale integration tests replaced: `tests/test_api_integration.py` removed (old battery payload, removed routes); still-valid coverage moved to `tests/test_api_db.py`, plus battery lifecycle and optimizer tests

### Fixed
- `DELETE /api/sources/{id}` always returned 500, and `POST /api/sources` with a `community_id` returned 500 ("no running event loop" when scheduling the simulator)
- `GET /api/device-status` always returned 500 (looked up a non-existent `wind` table)
- `POST /api/optimize` always returned 500 (treated CRUD lists as DataFrames)
- Optimizer counted EV charging as power sold to the grid, and gave the first hour's charge/discharge for free
- `load_pack` could not load any pack: `execute_values` got a connection instead of a cursor, readings omitted `community_id` values, and the schema rejected the builder's charge-only EVs
- Household load was generated from local time but stored as UTC (started 2 h in the future off Docker)
- `GET /api/realtime-data` without `since` returned the first 100 points ever stored instead of the latest
- Synthetic load from generate-system-data was wiped by the next household create/delete, and repeated calls duplicated market rows
- `save_household_load` never closed its database connection

### Removed
- Authentication and per-user data scoping (JWT login, `users` table, `user_id` / `manager_user_id` ownership checks). Last present in commit `951c9b8` (also local branch `feature/auth`); restore by reverting this commit.

---

## [3.0.0] — 2025-xx-xx  *(pre-deployment)*

### Added
- Authentication — JWT login with bcrypt password hashing (`/login`, `POST /auth/register`)
- Protected routes — all frontend pages require login (`ProtectedRoute`)
- Community dashboard — household aggregation view
- Household management — add/delete households, assign EVs
- Electric vehicle panel — charge/discharge SOC tracking
- Profiles tab — per-household load profiles
- Forecast tab — unified historical + forecasted data viewer
- Interactive 3D map (`Map3D`) as default landing page
- Traefik v3 reverse proxy with Let's Encrypt SSL (production)

### Changed
- Major frontend refactor — pages split into dedicated route components
- `CombinedDataViewer` — simplified `ForecastedDataPoint` interface (value instead of yhat)
- Dockerfiles slimmed down; dev/prod split into `docker/dev/` and `docker/prod/`
- Traefik upgraded from v2 to v3 (fixes Docker API compatibility)
- Consumer group renamed `test-group` (was `my-group`)

---

## [2.0.0] — 2024-xx-xx

### Added
- TimescaleDB hypertables for time-series data
- MLflow model registry integration
- Training pipeline with time-series cross-validation
- Inference pipeline with 30-step-ahead forecasting
- PuLP optimization for battery dispatch
- GitHub Actions CI with coverage badge (Gist)
- `pytest_postgresql` integration tests

### Changed
- Full API refactor — routes split by domain (`data`, `batteries`, `sources`, `optimization`)
- Forecast tables reset before each inference run

---

## [1.0.0] — 2024-xx-xx

### Added
- Initial microservices architecture
- FastAPI backend + React frontend
- Kafka streaming (solar, wind, load, market topics)
- Synthetic data generation via `pvlib` and `windpowerlib`
- Docker Compose orchestration
