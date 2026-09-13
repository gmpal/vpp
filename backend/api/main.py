import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import admin, batteries, community, data, forecasting, households, optimization, sources, vehicles, weather
from backend.src.db import DatabaseManager, SchemaManager
from backend.src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_core_tables():
    """Apply idempotent schema migrations for databases created by older versions."""
    try:
        db = DatabaseManager()
        schema = SchemaManager(db)
        schema._migrate_relax_legacy_user_scoping()
        schema._migrate_allow_charge_only_evs()
    except Exception as e:
        # The API still starts (the DB may come up later), but say so: migrations were skipped.
        logger.warning("Startup schema migrations skipped: %s", e)


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

        for row in rows:
            source_id, source_type, community_id, lat, lon = row
            await SimulatorManager.start_simulator(
                source_id=source_id,
                source_type=source_type,
                community_id=str(community_id),
                latitude=lat,
                longitude=lon,
            )
        if rows:
            logger.info("Resumed %d device simulators", len(rows))
    except Exception as e:
        logger.warning("Device simulators not resumed at startup (they start on demand): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_core_tables()
    await resume_active_simulators()
    yield


app = FastAPI(lifespan=lifespan)


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
app.include_router(batteries.router, prefix="/api")
app.include_router(community.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
