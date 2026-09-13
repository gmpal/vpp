# TODO — Industry-Grade Improvements

## High Priority — Features

- [ ] **`energy_sources` type constraint** — Schema locks `type` to `'solar'` only (`CHECK (type IN ('solar'))`). Extend to support `'wind'` and any future source types, or make it a FK to a source_types table.
- [ ] **Optimization endpoint** — Falls back to history when forecasts are missing (done 2026-09-13), but does not account for real-time EV SOC drift or partial charge sessions between runs.

## Backend — Known Issues (audit 2026-09-13)

Found while testing with the API console (`make console`). Completed items are recorded in `CHANGELOG.md`.

### Plan (agreed 2026-09-13)
1. **In progress** — data layer batch: batched inserts, latest-data semantics for `top`, stop generated load being wiped.
2. **Next** — forecasting status + silent startup hooks; community summary battery fields.
3. **On hold** — optimization model items (wear cost, discharge efficiency) until the uncommitted `dispatch()` / settlement work in `optimization.py` lands, to avoid conflicts.
4. **Filler** — wind leftovers, 4xx mapping for unknown series, ruff findings.
5. **Decision pending (maintainer)** — push `develop` / open a PR so CI runs the new tests against the disposable test DB.

### Bugs
- [ ] **Realtime endpoint returns the oldest data** — `GET /api/realtime-data/{source}` calls `load_historical_data(top=100)`, which orders by time ascending and limits, so without `since` it returns the first 100 points ever stored. `/api/historical?top=N` behaves the same.
- [ ] **Generated load is wiped by household changes** — `POST /api/data/generate-system-data` writes synthetic rows to `load`, but creating/deleting a household rebuilds `load` from `household_load` (DELETE first). Reset-db already treats load as household-derived; the endpoint should stop writing load.
- [ ] **Forecasting status reports success on failure** — `run_training` / `run_inference` ignore the subprocess return code and set `last_training` / `last_inference` anyway. Script paths (`/app/backend/...`) and the MLflow URI (`http://mlflow:5000`) are hardcoded, so they only work inside Docker.
- [ ] **Community summary ignores batteries** — `CrudManager.get_community_summary` never fills `battery_count`, `battery_soc_total`, `battery_soc_capacity`; they are always 0.

### Performance
- [ ] **Row-by-row inserts, one connection each** — `save_to_db` opens and commits a connection per row: reset/init-db ≈ 37 s for 2,400 market rows, generate-system-data ≈ 2.5 min. Batch with `execute_values`.
- [ ] **N+1 queries in `GET /api/sources`** — one extra query per source for its latest value.
- [ ] **Sync DB calls on the event loop** — `POST /api/sources` and `DELETE /api/sources/{id}` are `async def` (to schedule simulators) but call blocking psycopg2; short queries, but they block other requests meanwhile.

### Optimization model
- [ ] **No battery-wear cost** — with a very cheap refill ahead, V2G EVs sell charge early to make room (rational on price alone). Add a per-kWh throughput cost.
- [ ] **Discharge efficiency mismatch** — the optimizer applies `eta` only when charging; `/api/vehicles/{id}/discharge` also divides discharge by `eta`.
- [ ] **No departure targets** — no minimum final SOC or departure time per EV (option C from the 2026-09-13 design discussion).

### Correctness & cleanup
- [ ] **Unknown series names return 500** — `InvalidTableNameError` (e.g. `/api/forecasted/foo`) should map to 400/404.
- [ ] **Startup hooks fail silently** — both use `except Exception: pass`, so migrations and simulator restarts are skipped without a log line; they also use deprecated `@app.on_event` (move to lifespan).
- [ ] **Wind leftovers** — wind is unsupported but still referenced in `SchemaManager.FORECAST_TABLES`, the `community_id` migration and the `AddSourceRequest` comment.
- [ ] **`load_pack` is not re-runnable** — plain INSERTs; loading a pack twice fails on the first duplicate key.
- [ ] **Ruff** — 8 pre-existing findings (unused imports, import order, complexity in `build_packs` / `load_pack`).
- [ ] **Local dev ports** — on the maintainer's machine `.env` conflicts: port 8000 is used by another app and 5432 by a native Windows Postgres. Workaround: backend on 8001 against the test DB on 55432.

## High Priority — Tooling & Libraries

- [ ] **Dependency vulnerability remediation** — Current state: 9 known Python CVEs (fastapi, starlette, python-jose, python-multipart) + 51 npm vulnerabilities (24 high, 1 critical). Audit jobs set to `continue-on-error: true` in CI. Action: Upgrade fastapi/starlette, evaluate python-jose alternatives, pin safe package versions, then remove soft-fail flags in `.github/workflows/security.yaml`.
- [ ] **Database migrations (Alembic)** — Replace custom `SchemaManager` migration methods with versioned, reversible Alembic migrations. Current approach (`_migrate_add_user_id()` etc.) has no rollback path.
- [x] **Structured logging** — `logger.py` now emits JSON in production (`ENVIRONMENT=production`) via `python-json-logger`, coloured text in development. Zero call-site changes needed.
- [x] **Python linting (Ruff)** — Replaced Flake8 with `ruff` via `pyproject.toml` + CI lint job in `tests.yaml`. Deleted `.flake8`.
- [ ] **Python type checking (MyPy)** — Add `mypy --strict` to catch real bugs, especially around Pydantic models.
- [x] **Pre-commit hooks** — Added `.pre-commit-config.yaml` with ruff, ruff-format, prettier, and common file checks.

## Medium Priority — Tooling & Libraries

- [x] **Security scanning in CI** — Added `.github/workflows/security.yaml`: `pip-audit` (Python CVEs), `bandit` (SAST), `npm audit --audit-level=high`, `trivy` image scan. Runs on PR + weekly schedule.
- [ ] **Rate limiting** — No rate limiting on FastAPI endpoints. Add `slowapi` middleware to protect optimization/training endpoints from abuse.
- [ ] **Redis / caching layer** — Every request hits TimescaleDB directly. Add Redis for frequently-read endpoints (source data, forecasts), rate limiting state, and session storage.
- [ ] **Observability stack (Prometheus + Grafana)** — `prometheus_client` is in requirements but unused. Wire up `prometheus-fastapi-instrumentator`, add Prometheus + Grafana to docker-compose for request latency, error rates, DB query dashboards.
- [x] **Prettier (frontend)** — Integrated via pre-commit hook (mirrors-prettier), runs on `src/**/*.{ts,tsx,css,json}`.

## Lower Priority — Tooling & Libraries

- [ ] **Sentry** — Runtime error tracking with stack traces and context.
- [ ] **`.coveragerc`** — Configure coverage thresholds, fail CI below a minimum (e.g. 80%).
- [ ] **Terraform / Pulumi** — IaC if deployment moves beyond a single VPS.
- [ ] **Vault / SOPS** — Secrets management beyond plain `.env` files.
- [ ] **Dependabot / Renovate** — Automated dependency update PRs.
- [ ] **Health check endpoints** — Proper `/health` and `/ready` endpoints for container orchestration.

---

## CI/CD

### Missing Workflows

- [ ] **Frontend CI** — No workflow runs `npm test`, `npm run build`, or Playwright E2E tests. The full E2E suite in `frontend/e2e/` never runs in CI.
- [ ] **Lint / type check in CI** — No CI step runs Flake8 (configured but unenforced), mypy, or ESLint.
- [ ] **Docker build verification** — 11 Dockerfiles across dev/prod, none built in CI. Broken Dockerfiles only discovered at deploy time.
- [ ] **Security scanning workflow** — No `npm audit`, `pip-audit`/`safety`, `trivy`, or `bandit` in CI.
- [ ] **Deployment pipeline** — Deployment is entirely manual SSH. No automated deploy on merge, no staging environment, no smoke tests, no rollback mechanism.
- [ ] **Release management** — No GitHub Releases, no tags, no semantic versioning, no changelog generation.

### Target CI/CD Structure

```
.github/workflows/
├── ci.yaml              # Runs on every PR
│   ├── backend-lint     # ruff + mypy
│   ├── backend-test     # pytest + coverage (exists today)
│   ├── frontend-lint    # eslint + tsc --noEmit
│   ├── frontend-test    # jest unit tests
│   ├── frontend-e2e     # playwright
│   └── docker-build     # build all images, don't push
│
├── security.yaml        # Weekly or on PR
│   ├── pip-audit
│   ├── npm-audit
│   └── trivy image scan
│
├── deploy.yaml          # On merge to main
│   ├── build + push images to registry
│   ├── SSH deploy to VPS (or docker context)
│   └── smoke test (curl health endpoint)
│
└── release.yaml         # On tag push (v*)
    └── GitHub Release + changelog
```

### Quick Wins

- [x] Add Playwright E2E tests to CI (`.github/workflows/frontend.yaml`)
- [x] Add `npm run build` to CI (catches TypeScript errors before merge)
- [x] Add `docker compose build` step to CI (`.github/workflows/tests.yaml`)
  - [ ] Verify `docker-compose.prod.yaml` build doesn't require additional env vars beyond `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DOMAIN`
- [x] Add PR template (`.github/pull_request_template.md`)

---

## Documentation

### Missing Docs

- [x] **Architecture diagram** — Mermaid flowchart added to README.md, replaces bullet-list description.
- [ ] **ADRs (Architecture Decision Records)** — Document key decisions: why TimescaleDB over InfluxDB, why PuLP over OR-Tools, why Kafka over Redis Streams, etc. Add `docs/adr/` folder.
- [x] **`CONTRIBUTING.md`** — Created with branch naming, PR process, coding standards, test requirements.
- [x] **`CHANGELOG.md`** — Created with versioned history reconstructed from git log.
- [x] **Runbook / operations guide** — Created `RUNBOOK.md`: health checks, secret rotation, Kafka lag, MLflow rollback, TimescaleDB disk, backup/restore, update procedure.
- [x] **`.env.example` inline docs** — Added comments for all non-obvious vars. Fixed missing `/api` suffix on `REACT_APP_API_BASE_URL`.
- [x] **Frontend README** — Replaced CRA boilerplate with real docs: routes table, project structure, how to add a page, E2E test guide.
- [ ] **API docs beyond Swagger** — Document auth flows, error codes, rate limits. Swagger shows the shape, not the intent.
