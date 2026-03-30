# CLAUDE.md — Virtual Power Plant (VPP)

This file gives Claude (and other AI coding agents) the context needed to work effectively in this repository.

---

## What this project does

A **Virtual Power Plant (VPP)** simulation built as containerised microservices. It:

1. **Generates** synthetic time-series data for solar, wind, load, and electricity market prices.
2. **Streams** that data through Apache Kafka into a TimescaleDB (PostgreSQL) instance.
3. **Trains** time-series forecasting models (currently RandomForest via scikit-learn) and tracks experiments in MLflow.
4. **Generates forecasts** with the best registered model and persists them to the database.
5. **Optimises** battery charge/discharge schedules and grid trading via linear programming (PuLP).
6. **Exposes** everything through a FastAPI REST API consumed by a React/TypeScript frontend.

---

## Repository layout

```
vpp/
├── backend/
│   ├── api/                  # FastAPI application
│   │   ├── main.py           # App factory: registers all routers, CORS middleware
│   │   ├── models.py         # Pydantic request/response schemas
│   │   └── routes/           # One file per domain
│   │       ├── admin.py      # POST /api/admin/init-db
│   │       ├── community.py  # GET  /api/community/summary
│   │       ├── data.py       # GET  /api/realtime-data, /historical, /forecasted
│   │       ├── forecasting.py# POST /api/train, GET /api/training-status, POST /api/run-inference
│   │       ├── households.py # CRUD /api/households
│   │       ├── optimization.py# POST /api/optimize
│   │       ├── sources.py    # POST /api/sources
│   │       ├── vehicles.py   # CRUD /api/vehicles + POST /api/vehicles/{id}/charge
│   │       └── weather.py    # GET  /api/weather/current, /api/weather/forecast
│   └── src/                  # Core business logic
│       ├── config.py         # Pydantic Settings singleton (get_settings())
│       ├── dependencies.py   # FastAPI DI: DatabaseManager, CrudManager, SchemaManager singletons
│       ├── exceptions.py     # Custom exception hierarchy rooted at VPPException
│       ├── db/
│       │   ├── connection.py # DatabaseManager — thin psycopg2 wrapper
│       │   ├── crud.py       # CrudManager — all SQL reads/writes (table whitelist enforced)
│       │   └── schema.py     # SchemaManager — creates hypertables & regular tables
│       ├── forecasting/
│       │   ├── feature_engineering.py  # Cyclical time features, holiday flags
│       │   └── models/
│       │       ├── base.py   # Abstract BaseTimeSeriesModel (train/predict/evaluate/tune)
│       │       ├── rf.py     # RandomForestTimeSeriesModel  ← only active model
│       │       ├── arima.py  # ARIMATimeSeriesModel         (inactive / commented out)
│       │       ├── prophet.py# ProphetTimeSeriesModel       (inactive / commented out)
│       │       ├── mlp.py    # MLPTimeSeriesModel           (inactive / commented out)
│       │       └── tft.py    # TFTTimeSeriesModel           (stub / incomplete)
│       ├── optimization/
│       │   └── optimization.py  # PuLP LP solver; optimize() + load_optimization_data()
│       ├── pipelines/
│       │   ├── generation.py    # Synthetic data generation (pvlib, windpowerlib)
│       │   ├── inference.py     # Load MLflow model → 30-step forecast → DB
│       │   └── training.py      # TimeSeriesSplit CV → best model → MLflow registry
│       ├── storage/
│       │   └── battery.py       # Battery class: SOC tracking, charge/discharge
│       ├── streaming/
│       │   ├── communication.py # Kafka producer utilities
│       │   ├── create_topics.py # Initialise Kafka topics
│       │   ├── sources.py       # create_new_source() → weather + PV data + Kafka producer
│       │   └── start.py         # Bulk-load CSVs to DB then start streaming
│       └── utils/
│           ├── data_utils.py    # get_datasets_list() and misc helpers
│           └── logger.py        # Coloured, file+console logging (get_logger())
├── frontend/                 # React 19 + TypeScript SPA
│   └── src/
│       ├── App.tsx            # Router + sidebar layout
│       ├── api.ts             # Axios client for backend REST API
│       └── components/        # Map3D, HouseholdPanel, VehiclePanel, EVCard, …
├── tests/                    # Pytest suite (see Testing section below)
├── entrypoints/              # Shell scripts run inside Docker containers
├── docker/                   # Dockerfiles (one per service)
├── docker-compose.yaml       # Full local stack
├── docker-compose.prod.yaml  # Production overrides
├── k8s/                      # Kubernetes manifests
├── requirements/             # Python dependency files
└── pytest.ini                # pythonpath = .
```

---

## How to run things

### Run the full stack locally

```bash
# 1. Core infrastructure
docker-compose up -d timescaledb zookeeper kafka mlflow

# 2. Kafka consumer
docker-compose up -d consumer

# 3. Seed DB and start streaming (run once, foreground to watch logs)
docker-compose --profile init up db-init

# 4. Application services
docker-compose up -d backend frontend

# 5. (Optional) trigger ML pipelines on demand
docker-compose --profile task up --no-deps training
docker-compose --profile task up --no-deps inference
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API (Swagger) | http://localhost:8000/docs |
| MLflow UI | http://localhost:5000 |

### Run the backend outside Docker

```bash
# Requires a running TimescaleDB and appropriate env vars
POSTGRES_DB=vpp POSTGRES_USER=postgres POSTGRES_PASSWORD=pass \
  uvicorn backend.api.main:app --reload --port 8000
```

---

## Testing

Tests live in `tests/` and use **pytest**. The `pythonpath` is set to `.` (repo root) in `pytest.ini`, so all imports use the `backend.` namespace.

### Run all tests

```bash
pytest tests/
```

### Run a single file

```bash
pytest tests/test_api_unit.py
```

### Key test files

| File | What it covers |
|------|----------------|
| `test_api_unit.py` | FastAPI endpoints with mocked dependencies |
| `test_api_integration.py` | Historical/forecasted data + battery endpoints |
| `test_api_db.py` | API + real database integration |
| `test_db_crud.py` | CrudManager SQL operations |
| `test_db_schema.py` | Schema creation and hypertable setup |
| `test_households.py` | Household CRUD |
| `test_vehicles.py` | EV creation, charging, status |
| `test_community_weather.py` | Community summary + weather endpoints |
| `test_feature_engineering.py` | Time feature creation |
| `test_data_generation.py` | Synthetic solar/wind/load/market generation |
| `test_kafka_utils.py` | Kafka producer utilities |

### Database fixtures (`conftest.py`)

Tests that touch the database need a live TimescaleDB reachable via:

```
POSTGRES_DB     (default: postgres)
POSTGRES_USER   (default: postgres)
POSTGRES_PASSWORD (default: testpass)
TIMESCALEDB_HOST (default: localhost)
POSTGRES_PORT   (default: 5432)
```

The `db_connection` fixture (module-scoped) creates a connection, enables the `timescaledb` extension, and tears down all tables in `public` at the end.

---

## Configuration

All runtime config is managed by **`backend/src/config.py`** using Pydantic Settings. Values are read from environment variables (case-insensitive). Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | *(required)* | Database name |
| `POSTGRES_USER` | *(required)* | Database user |
| `POSTGRES_PASSWORD` | *(required)* | Database password |
| `TIMESCALEDB_HOST` | `localhost` | DB host |
| `POSTGRES_PORT` | `5432` | DB port |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:29092` | Kafka broker address |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow server |
| `LOG_LEVEL` | `INFO` | One of DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `ENVIRONMENT` | `development` | `development` / `production` / `testing` |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins for the backend |

Use `get_settings()` to access the singleton; avoid importing `settings` directly at module level in places that run under test (prefer `Depends(get_settings)` in FastAPI routes).

---

## Known TODOs / incomplete areas

- **`optimization/optimization.py`**: The time frequency (currently 5-minute intervals from the inference pipeline) should be harmonised to hourly when extending the forecasting window. Two `TODO` comments mark the exact spots.
- **`pipelines/generation.py`**: `read_generation_config()` has placeholder config-parsing code; actual config.ini values are not yet wired up.
- **`pipelines/training.py`**: ARIMA, Prophet, MLP, and TFT models are all commented out of the `model_configs` list. Only `RandomForestTimeSeriesModel` is active.
- **`forecasting/models/tft.py`**: The `objective()` function for Optuna hyperparameter tuning is a stub and needs to be adapted to the `BaseTimeSeriesModel` interface.
- **`forecasting/models/prophet.py`**: A `TODO` notes that frequencies need to be harmonised across model types.
- **Weather endpoint** (`routes/weather.py`): Falls back to synthetic data when `OPENWEATHERMAP_API_KEY` is not set. The key is not yet part of `config.py`.
- **No connection pooling**: `DatabaseManager` creates a new psycopg2 connection on each call. Consider `psycopg2.pool` or `asyncpg` for production.
- **No API rate limiting**: Endpoints that trigger long-running tasks (train, inference) have no guard against concurrent or rapid invocations.

---

## Architecture decisions to be aware of

1. **Table whitelist in CrudManager**: `crud.py` validates table names against a hard-coded whitelist before executing any query. When adding a new table, update the whitelist in `CrudManager`.

2. **Dependency injection pattern**: `dependencies.py` exposes `get_db_manager()`, `get_crud_manager()`, and `get_schema_manager()` as FastAPI `Depends` callables. Routes should use these rather than instantiating managers directly.

3. **MLflow model naming convention**: Models are registered as `{source}_forecast` (e.g., `solar_forecast`, `load_forecast`, `market_forecast`) in the MLflow Model Registry. The inference pipeline loads models by these names using the `Production` stage alias.

4. **Hypertables**: TimescaleDB hypertables partition on the `time` column. The `SchemaManager` creates them with `create_hypertable()`. Do not rename the `time` column without updating `schema.py`.

5. **CORS**: In production set the `ALLOWED_ORIGINS` environment variable to the actual frontend origin (e.g., `https://vpp.digital`). The default `*` is intentional for local development only.

6. **Frontend API client** (`frontend/src/api.ts`): All backend calls go through this single Axios instance. When adding a new backend endpoint, add the corresponding function here.

---
