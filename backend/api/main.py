import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import sources, data, optimization, forecasting
from backend.api.routes import households, vehicles, community, weather, admin

app = FastAPI()

# In production set ALLOWED_ORIGINS=https://vpp.digital in the environment.
# Defaults to * for local development.
_raw = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in _raw.split(",")]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (keep it simple here)
@app.get("/health")
def health_check():
    return {"status": "ok"}


# Mount route modules
app.include_router(sources.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
app.include_router(forecasting.router, prefix="/api")
app.include_router(households.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(community.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
