# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A containerized microservices system simulating a Virtual Power Plant (VPP). The system integrates synthetic data generation, Kafka streaming, ML forecasting with MLflow, and PuLP optimization for distributed energy resource management.

## Core Architecture

### Microservices Structure

The system comprises independent Docker services that communicate via REST APIs and Kafka:

- **backend** (FastAPI): REST API server, handles frontend requests, interacts with TimescaleDB and MLflow
- **frontend** (React/TypeScript): User interface for monitoring and managing the VPP
- **db-init**: One-time initialization service that creates database schema and starts Kafka producers for synthetic data streaming (profile: `init`)
- **consumer**: Centralized Kafka consumer that writes all incoming data (solar, wind, load, market) to TimescaleDB
- **training**: ML pipeline that trains forecasting models using time-series cross-validation and registers best models in MLflow (profile: `task`)
- **inference**: ML pipeline that loads models from MLflow and generates 30-step-ahead forecasts (profile: `task`)
- **Infrastructure**: timescaledb (time-series DB), kafka + zookeeper (messaging), mlflow (ML model registry)

### Docker Compose Profiles

Services are organized by profiles to control when they run:
- **No profile** (default): Always-running services (backend, frontend, consumer, infrastructure)
- **init**: One-time initialization (db-init) - run once at setup
- **task**: On-demand ML pipelines (training, inference) - trigger manually or via scheduler

### Data Flow

1. **db-init** generates synthetic data using `pvlib` (solar) and `windpowerlib` (wind), then produces to Kafka topics
2. **consumer** listens to Kafka topics (`solar`, `wind`, `load`, `market`) and writes to TimescaleDB hypertables
3. **training-pipeline** performs time-series CV on historical data, compares models, and registers the best model per dataset/source_id in MLflow
4. **inference-pipeline** fetches latest models from MLflow Registry and saves forecasts to `*_forecast` tables
5. **backend** serves historical and forecasted data to frontend, runs optimization on demand
6. **frontend** displays data visualizations and allows users to add batteries/sources

### Key Design Patterns

**Database Schema**: TimescaleDB hypertables partitioned by `time` column. Renewable sources have `source_id` to support multiple generators. Non-renewable data (load, market) have no source_id. Forecast tables mirror this structure with `yhat` instead of `value`.

**Model Registry Pattern**: Each dataset-source_id pair gets a unique MLflow registry name (e.g., `Best_solar_010780_Model`, `Best_load_Model`). Training pipeline registers models after full dataset retraining. Inference pipeline loads by registry name and version.

**Forecasting Models**: All models inherit from `BaseTimeSeriesModel` (backend/src/forecasting/models/base.py) which enforces `tune()`, `train()`, `evaluate()`, and `predict()` interface. Models are serialized as pickle files and stored in MLflow artifacts.

**Optimization**: PuLP linear programming minimizes total cost `sum(price[t] * (grid_buy[t] - grid_sell[t]))` subject to battery SOC dynamics, charge/discharge limits, and grid balance constraints. Uses big-M formulation to enforce buy/sell exclusivity.

## Development Commands

### Docker Compose Workflows

**Initial Setup** (run in order):
```bash
# 1. Create .env file in root directory with required environment variables
# See .env file for reference configuration

# 2. Start infrastructure
docker-compose up -d timescaledb zookeeper kafka mlflow

# 3. Start consumer (listens to Kafka)
docker-compose up -d consumer

# 4. Initialize database and start data streaming (run once)
docker-compose --profile init up db-init

# 5. Start application
docker-compose up -d backend frontend
```

**ML Pipeline Execution** (on-demand tasks, can also be scheduled):
```bash
# Train models (performs CV, registers in MLflow)
docker-compose --profile task up training

# Generate forecasts (loads models, writes to DB)
docker-compose --profile task up inference
```

**Development**:
```bash
# Rebuild specific service after code changes
docker-compose build <service_name>

# View logs
docker-compose logs -f <service_name>

# Restart service
docker-compose restart <service_name>

# Stop all services
docker-compose down

# Stop and remove volumes (full database reset)
docker-compose down -v

# Check running services
docker-compose ps
```

**Windows-Specific Notes**:
- Use PowerShell or Git Bash for running Docker commands
- Ensure Docker Desktop is running before executing commands
- File paths in volume mounts use forward slashes (/) even on Windows
- Line endings: Git should be configured to handle CRLF conversion (core.autocrlf=true or input)

### Testing

**Python (Backend)**:
```bash
# Run all tests
pytest

# Run specific test file
pytest backend/tests/test_<module>.py

# Run with coverage
pytest --cov=backend

# Run in Docker container
docker-compose exec backend pytest
```

**React (Frontend) — Unit Tests**:
```bash
# Inside frontend directory or container
npm test

# Run tests in CI mode
npm test -- --coverage --watchAll=false

# In Docker
docker-compose exec frontend npm test
```

**React (Frontend) — E2E Tests (Playwright)**:
```bash
cd frontend

# First-time setup: install Playwright browsers
npx playwright install chromium

# Run all E2E tests (headless — for CI and quick checks)
npm run test:e2e

# Run with visible browser (debugging)
npm run test:e2e:headed

# Run with Playwright interactive UI
npm run test:e2e:ui
```

E2E tests live in `frontend/e2e/` and mock all backend API calls, so **no backend needed**.
- `fixtures.ts` — shared API mock setup (reuse in new tests via `mockAllApis(page)`)
- `navigation.spec.ts` — sidebar navigation to all routes
- `pages.spec.ts` — each page renders its main heading
- `sidebar-actions.spec.ts` — Init DB dialog, Reset confirmation, Train/Inference loading states
- `households.spec.ts` — add/delete households, add EVs via dialog
- `vehicles.spec.ts` — vehicle display, charge/discharge SOC updates, disabled state at full charge
- `optimization.spec.ts` — run optimization, view chart/table, error handling
- `data-viewing.spec.ts` — Renewables source switching, Grid dual charts, Profiles triple charts, Forecast viewer
- `full-pipeline.spec.ts` — multi-page journeys: init→train→infer→forecast, add household→view vehicles

Config: `frontend/playwright.config.ts` — auto-starts React dev server, runs Chromium.

**Important**: The frontend `.env` sets `REACT_APP_API_BASE_URL=http://localhost:8000/api` (note the `/api` prefix). All API mocks must use `http://localhost:8000/api/...` routes, not `http://localhost:8000/...`.

### Local Development (Outside Docker)

**Backend**:
```bash
# Install dependencies
pip install -r requirements/requirements-backend.txt

# Run FastAPI with auto-reload
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm start  # Runs on localhost:3000
```

## Important File Locations

### Backend Code Organization

- `backend/api/main.py`: FastAPI application entry point with CORS and route mounting
- `backend/api/routes/`: API endpoints split by domain (batteries, sources, data, optimization)
- `backend/src/db/schema.py`: TimescaleDB schema definition with hypertable creation
- `backend/src/db/crud.py`: Database CRUD operations for historical/forecasted data
- `backend/src/pipelines/training.py`: Model training with time-series cross-validation
- `backend/src/pipelines/inference.py`: Model loading from MLflow and forecast generation
- `backend/src/forecasting/models/`: Time-series model implementations (RF, ARIMA, Prophet, MLP, TFT)
- `backend/src/optimization/optimization.py`: PuLP linear programming for battery/grid dispatch
- `backend/src/streaming/communication.py`: Kafka producer/consumer implementations
- `backend/src/storage/battery.py`: Battery class with charge/discharge logic

### Frontend Code Organization

- `frontend/src/App.tsx`: Main application with routing
- `frontend/src/Dashboard.tsx`: Main dashboard for adding resources and viewing status
- `frontend/src/CombinedDataViewer.tsx`: Unified viewer for historical + forecasted data
- `frontend/src/Optimization.tsx`: UI for triggering and viewing optimization results
- `frontend/src/BatteryManagement.tsx`: Battery control interface
- `frontend/src/api.ts`: Axios API client for backend communication

### Configuration

- `docker-compose.yaml`: Service orchestration with dev/prod Dockerfiles and service profiles (`init`, `task`)
- `.env`: Environment variables (POSTGRES credentials, KAFKA_PORT, MLFLOW_PORT, etc.) - **Required** before starting services
- `requirements/`: Separate requirement files per service (backend, consumer, forecasting)
- `docker/dev/`: Development Dockerfiles for each service
- `docker/prod/`: Production-optimized Dockerfiles

### Required Environment Variables

The `.env` file must include:
- Port mappings: `FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, `KAFKA_PORT`, `MLFLOW_PORT`, `ZOOKEEPER_CLIENT_PORT`
- Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `TIMESCALEDB_HOST`
- Kafka: `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_ADVERTISED_LISTENERS`
- MLflow: `MLFLOW_TRACKING_URI`, `MLFLOW_BACKEND_STORE_URI`, `MLFLOW_DEFAULT_ARTIFACT_ROOT`
- Frontend: `REACT_APP_API_BASE_URL`

## Important Implementation Notes

### Database Considerations

- Always use parameterized queries in `crud.py` to prevent SQL injection
- TimescaleDB hypertables require `SELECT create_hypertable()` after table creation (handled in schema.py)
- Forecast tables are reset via `schema_manager.reset_forecast_tables()` before each inference run
- Battery state is stored with DELETE-then-INSERT pattern (only one row per battery_id)
- Schema initialization is handled by `db-init` service and must complete before other services query the database
- Health check ensures database is ready before dependent services start

### MLflow Integration

- Models are stored as pickle files in MLflow artifacts (not using MLflow's native sklearn logging)
- Registry names follow pattern: `Best_{dataset}_{source_id}_Model` or `Best_{dataset}_Model`
- Training logs metrics per fold: `{dataset}_{model_name}_fold_{idx}_mse` and `{dataset}_{model_name}_avg_cv_mse`
- Inference pipeline loads models by registry name and stage (default: "None")

### Kafka Configuration

- Internal services use `kafka:29092` (PLAINTEXT listener)
- External/host access uses `localhost:${KAFKA_PORT}` (PLAINTEXT_HOST listener, default 9092)
- Topics: `solar`, `wind`, `load`, `market`
- Consumer group: `test-group` (previously `my-group`)
- Replication factor: 1 (single broker setup)
- **Critical**: Always use `kafka:29092` in Docker service environment variables, never `localhost`

### Frontend-Backend Communication

- Backend runs on port 8000 (internal Docker), exposed via `BACKEND_PORT` env var
- Frontend expects `REACT_APP_API_BASE_URL` env var for API base URL
- CORS allows all origins (`allow_origins=["*"]`) for development

### Optimization Constraints

- Battery SOC update: `SOC(t) = SOC(t-1) + η * Charge(t) - Discharge(t)`
- Net excess: `solar + wind - load + Σ(Charge - Discharge)`
- Grid buy/sell are mutually exclusive (big-M formulation with binary variable `delta`)
- All batteries share grid buy/sell decisions (single aggregator)

## Interactive Map Feature

The frontend includes an **interactive map interface** for visual VPP management:
- **Main view**: http://localhost:3000 (interactive map with Leaflet.js)
- **Click-to-add**: Click anywhere on the map to place solar/wind sources with real coordinates
- **Real-time visualization**: Pulsing circles show current production, sized by output
- **Location-aware data**: Synthetic data generation uses actual lat/lon for realistic values
- **Full CRUD**: Add, view, and delete sources directly from map popups
- **API endpoints**:
  - `GET /sources` - List all sources with locations and current production
  - `POST /sources` - Add source with coordinates
  - `DELETE /sources/{id}` - Remove source and all data

See `MAP_FEATURE.md` for detailed documentation.

## Access Points

When services are running:
- **Interactive Map**: http://localhost:3000 (default view)
- Dashboard: http://localhost:3000/dashboard
- Backend API Docs: http://localhost:8000/docs
- MLflow UI: http://localhost:5000
- TimescaleDB: localhost:5432 (credentials in .env)
- Kafka: localhost:9092 (external), kafka:29092 (internal)

## Common Troubleshooting

- **Missing .env file**: Create `.env` in root directory with all required variables before starting services
- **db-init fails**: Check that timescaledb is healthy with `docker-compose logs timescaledb`
- **Consumer not writing data**: Verify Kafka topics exist and db-init producers are running
- **Training fails with "No data found"**: Ensure db-init completed successfully and consumer has been running long enough to accumulate data
- **Inference fails**: Ensure training has run at least once to register models in MLflow
- **Frontend shows no data**: Check backend logs for database connection errors with `docker-compose logs backend`
- **Kafka connection issues**: Internal services must use `kafka:29092`, external/host uses `localhost:${KAFKA_PORT}`
- **Service dependency issues**: Always start services in order (infrastructure → consumer → db-init → application)
- **Port conflicts**: Check that ports defined in `.env` are not already in use on your system
