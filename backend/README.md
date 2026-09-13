The backend has two main folders under backend/:

backend/
├── api/
│   ├── main.py              ← FastAPI app, CORS, startup hooks
│   ├── models.py            ← Pydantic request/response schemas
│   └── routes/              ← one file per resource
│       ├── sources.py       ← energy sources (solar, wind…)
│       ├── households.py
│       ├── batteries.py
│       ├── vehicles.py
│       ├── community.py
│       ├── weather.py       ← Open-Meteo (in-flight, uncommitted)
│       ├── data.py          ← historical reads
│       ├── forecasting.py
│       ├── optimization.py  ← LP dispatch
│       └── admin.py         ← data generation triggers
│
└── src/
    ├── db/                  ← connection, schema, CRUD
    ├── streaming/           ← DeviceSimulator, SimulatorManager, Kafka
    ├── forecasting/         ← models (ARIMA, RF, MLP, Prophet, TFT)
    ├── pipelines/           ← training, inference, generation scripts
    ├── optimization/        ← LP battery dispatch (PuLP)
    ├── storage/             ← Battery state class
    └── config.py / dependencies.py
## Testing

The backend test suite is independent of the frontend and of the repository
`.env`. Run it from the repository root.

```bash
pip install -r requirements/requirements-test.txt

make test-unit   # no database, Kafka, network or .env needed
make test-int    # starts a disposable TimescaleDB on port 55432, runs integration tests
make test        # both tiers
make test-db-down
```

- **Unit tests** are every test not marked `integration`. They cannot open a
  database connection or reach the internet; attempts raise immediately.
- **Integration tests** are marked `integration` or use the database fixtures
  in `tests/conftest.py`. Without a reachable test database they are skipped.
- The test database is configured with `VPP_TEST_DB_HOST`, `VPP_TEST_DB_PORT`,
  `VPP_TEST_DB_NAME`, `VPP_TEST_DB_USER` and `VPP_TEST_DB_PASSWORD`. Never point
  these at a real database: the fixtures drop every table in `public`.
