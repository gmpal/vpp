# TODO — Industry-Grade Improvements

## High Priority — Features

- [ ] **`energy_sources` type constraint** — Schema locks `type` to `'solar'` only (`CHECK (type IN ('solar'))`). Extend to support `'wind'` and any future source types, or make it a FK to a source_types table.
- [ ] **Optimization endpoint** — `optimize()` uses forecast data only; does not account for real-time EV SOC drift or partial charge sessions between runs.

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
