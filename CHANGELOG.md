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
