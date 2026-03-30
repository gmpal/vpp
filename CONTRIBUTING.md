# Contributing

## Getting Started

1. Fork the repo and clone it locally
2. Copy `.env.example` to `.env` and fill in values
3. Start the stack: follow the [Installation and Setup](README.md#installation-and-setup) steps
4. Install pre-commit hooks (required):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Branch Naming

```
feat/<short-description>     # new feature
fix/<short-description>      # bug fix
refactor/<short-description> # refactoring, no behaviour change
docs/<short-description>     # documentation only
chore/<short-description>    # tooling, deps, CI
```

All branches should be cut from `main`.

## Making Changes

### Backend

- Code lives in `backend/`
- Run tests before opening a PR:
  ```bash
  pytest
  ```
- Add tests for new behaviour — integration tests use a real TimescaleDB instance (see `tests/conftest.py`)
- Use parameterized queries in `crud.py` — no string formatting in SQL

### Frontend

- Code lives in `frontend/src/`
- Run unit tests:
  ```bash
  cd frontend && npm test -- --watchAll=false
  ```
- Run E2E tests (no backend required — all API calls are mocked):
  ```bash
  cd frontend && npm run test:e2e
  ```
- Add API mocks for new endpoints in `frontend/e2e/fixtures.ts`

### ML Pipelines

- Training code: `backend/src/pipelines/training.py`
- Inference code: `backend/src/pipelines/inference.py`
- All models must inherit from `BaseTimeSeriesModel` (`backend/src/forecasting/models/base.py`) and implement `tune()`, `train()`, `evaluate()`, `predict()`

## Code Style

Python and TypeScript are enforced automatically by pre-commit:

- **Python**: `ruff` (lint + format). Runs on commit. To run manually: `ruff check . --fix`
- **TypeScript/TSX**: `prettier`. Runs on commit. To run manually: `cd frontend && npx prettier --write src/`

CI will fail on lint errors — fix them locally before pushing.

## Pull Requests

- Fill in the PR template (appears automatically)
- Keep PRs focused — one concern per PR
- All CI checks must pass before merge:
  - `Backend CI` — pytest + ruff + docker build
  - `Frontend CI` — build + Playwright E2E
- A passing test suite is required; new features need new tests

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Relevant logs (`docker-compose logs <service>`)
