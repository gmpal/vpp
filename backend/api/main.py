import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import admin, auth, batteries, community, data, forecasting, households, optimization, sources, vehicles, weather
from backend.src.db import DatabaseManager, SchemaManager

app = FastAPI()


@app.on_event("startup")
def ensure_core_tables():
    """Ensure the users table and user_id migrations are applied on startup."""
    try:
        db = DatabaseManager()
        schema = SchemaManager(db)
        schema._create_users_table()
        schema._migrate_add_user_id()
        db.close()
    except Exception:
        pass  # DB may not be available yet; auth routes will fail gracefully


@app.on_event("startup")
async def resume_active_simulators():
    """On startup, restart device simulators for all active energy sources."""
    try:
        from backend.src.streaming.simulator_manager import SimulatorManager

        db = DatabaseManager()
        rows = db.execute(
            """
            SELECT source_id, type, community_id, latitude, longitude
            FROM energy_sources
            WHERE community_id IS NOT NULL
            """,
            fetch=True,
        ) or []
        db.close()

        for row in rows:
            source_id, source_type, community_id, lat, lon = row
            await SimulatorManager.start_simulator(
                source_id=source_id,
                source_type=source_type,
                community_id=str(community_id),
                latitude=lat,
                longitude=lon,
            )
    except Exception:
        pass  # DB not ready or no sources yet — simulators will be started on demand


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
app.include_router(auth.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
app.include_router(forecasting.router, prefix="/api")
app.include_router(households.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(batteries.router, prefix="/api")
app.include_router(community.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
