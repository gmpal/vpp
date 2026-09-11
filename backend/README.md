The backend has two main folders under backend/:

backend/
├── api/
│   ├── main.py              ← FastAPI app, CORS, startup hooks
│   ├── auth.py              ← JWT middleware
│   ├── models.py            ← Pydantic request/response schemas
│   └── routes/              ← one file per resource
│       ├── auth.py          ← login/register
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