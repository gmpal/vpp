# Phase 1 Implementation Plan: Community Entity + Real-time Device Simulation

## Overview
Transform from user-centric data to community-centric. Add `Community` table, scope all data by community, replace CSV replay with 1-per-second device simulator.

---

## A. Database Schema Changes

### New table: `communities`
```sql
CREATE TABLE communities (
  community_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_user_id VARCHAR UNIQUE NOT NULL,  -- FK to users.user_id
  name VARCHAR NOT NULL,
  location_lat FLOAT,
  location_lon FLOAT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Add `community_id` to existing tables:
```sql
ALTER TABLE households ADD COLUMN community_id UUID REFERENCES communities;
ALTER TABLE energy_sources ADD COLUMN community_id UUID REFERENCES communities;
ALTER TABLE batteries ADD COLUMN community_id UUID REFERENCES communities;

-- Update hypertables
ALTER TABLE solar ADD COLUMN community_id UUID;
ALTER TABLE wind ADD COLUMN community_id UUID;
ALTER TABLE load ADD COLUMN community_id UUID;
ALTER TABLE solar_forecast ADD COLUMN community_id UUID;
ALTER TABLE wind_forecast ADD COLUMN community_id UUID;
ALTER TABLE load_forecast ADD COLUMN community_id UUID;

-- Market stays GLOBAL (no community_id)

-- Add constraints where needed
ALTER TABLE households ADD CONSTRAINT fk_households_community 
  FOREIGN KEY (community_id) REFERENCES communities;
```

### Migration strategy:
- Write a SQL script that runs on startup (like `_migrate_add_user_id()`)
- `_migrate_add_community_id()` — for existing data:
  - If `energy_sources.user_id` exists, lookup that user's community (or create one)
  - Backfill `community_id` on all related rows
  - If no community exists yet for a user, create a "default" one

---

## B. API Model Changes

### New Pydantic models (`backend/api/models.py`):

```python
class CommunityCreate(BaseModel):
    name: str
    location_lat: float = None
    location_lon: float = None

class Community(BaseModel):
    community_id: str
    manager_user_id: str
    name: str
    location_lat: float
    location_lon: float
    created_at: datetime
```

### Update existing models to include `community_id`:
```python
class EnergySource(BaseModel):
    source_id: str
    community_id: str  # ADD THIS
    source_type: str
    # ... rest

class Household(BaseModel):
    household_id: str
    community_id: str  # ADD THIS
    # ... rest
```

---

## C. New Routes

### New file: `backend/api/routes/communities.py`

```python
@router.post("/communities", response_model=Community)
def create_community(req: CommunityCreate, current_user: dict = Depends(get_current_user)):
    """Manager creates a community. Community starts empty."""
    community_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO communities (community_id, manager_user_id, name, location_lat, location_lon) "
        "VALUES (%s, %s, %s, %s, %s)",
        (community_id, current_user["user_id"], req.name, req.location_lat, req.location_lon)
    )
    return get_community(community_id, current_user)

@router.get("/communities/{community_id}", response_model=Community)
def get_community(community_id: str, current_user: dict = Depends(get_current_user)):
    """Get community details. Manager-only."""
    row = db.execute(
        "SELECT * FROM communities WHERE community_id = %s AND manager_user_id = %s",
        (community_id, current_user["user_id"]),
        fetch=True
    )
    if not row:
        raise HTTPException(404, "Community not found")
    return Community(**dict(row))

@router.get("/communities", response_model=list[Community])
def list_communities(current_user: dict = Depends(get_current_user)):
    """List all communities managed by this user."""
    rows = db.execute(
        "SELECT * FROM communities WHERE manager_user_id = %s ORDER BY created_at DESC",
        (current_user["user_id"],),
        fetch=True
    )
    return [Community(**dict(r)) for r in rows]
```

Mount in `backend/api/main.py`:
```python
app.include_router(communities.router, prefix="/api")
```

---

## D. Update Existing Routes

### `sources.py`, `households.py`, `batteries.py`:
- All POST endpoints now require `community_id` in request body
- All GET endpoints filter by `current_user["user_id"]` AND scoped to their community
- Validation: ensure source/household/battery belongs to a community the user manages

### Example (`sources.py`):
```python
@router.post("/sources", response_model=EnergySourceWithData)
def add_source(
    request: AddSourceRequest,  # Now includes community_id
    crud = Depends(get_crud_manager),
    current_user = Depends(get_current_user)
):
    # Verify community belongs to user
    community = db.execute(
        "SELECT * FROM communities WHERE community_id = %s AND manager_user_id = %s",
        (request.community_id, current_user["user_id"]),
        fetch=True
    )
    if not community:
        raise HTTPException(403, "Community not found or access denied")
    
    # Create source (device simulator auto-starts below)
    source_id, _ = create_new_source(...)
    db.execute(
        "INSERT INTO energy_sources (source_id, type, ..., community_id, user_id) "
        "VALUES (%s, %s, ..., %s, %s)",
        (..., request.community_id, current_user["user_id"])
    )
    return ...
```

---

## E. Streaming: Device Simulator + Consumer Refactor

### New file: `backend/src/streaming/device_simulator.py`

```python
import asyncio
import json
from kafka import KafkaProducer
from datetime import datetime
import numpy as np

class DeviceSimulator:
    """Simulates a real IoT device (inverter, smart meter) emitting readings every second."""
    
    def __init__(self, source_id: str, source_type: str, community_id: str, 
                 latitude: float, longitude: float, capacity_kw: float = 10):
        self.source_id = source_id
        self.source_type = source_type  # "solar", "wind", "load"
        self.community_id = community_id
        self.latitude = latitude
        self.longitude = longitude
        self.capacity_kw = capacity_kw
        self.producer = KafkaProducer(
            bootstrap_servers='kafka:29092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.running = False
        self.time_idx = 0
    
    async def run(self):
        """Emit one reading per second (real-time simulation)."""
        self.running = True
        while self.running:
            # Generate synthetic reading based on source_type
            if self.source_type == "solar":
                value = self._generate_solar_reading()
            elif self.source_type == "wind":
                value = self._generate_wind_reading()
            elif self.source_type == "load":
                value = self._generate_load_reading()
            else:
                value = 0
            
            # Publish to Kafka
            message = {
                "device_id": self.source_id,
                "device_type": self.source_type,
                "community_id": self.community_id,
                "source_id": self.source_id,
                "value": value,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            self.producer.send("device_readings", value=message)
            print(f"[{self.source_type}] {self.source_id}: {value} kW")
            
            self.time_idx += 1
            await asyncio.sleep(1)  # One reading per real second
    
    def stop(self):
        self.running = False
    
    def _generate_solar_reading(self) -> float:
        """Use pvlib to generate realistic solar output."""
        # Simulate a day: peak at noon, zero at night
        import math
        hour_of_day = (self.time_idx % 86400) / 3600  # 0-24
        # Bell curve centered at 12
        solar_factor = max(0, math.cos((hour_of_day - 12) / 6 * math.pi / 2) ** 2)
        noise = np.random.normal(0, 0.1)
        return max(0, self.capacity_kw * solar_factor + noise)
    
    def _generate_wind_reading(self) -> float:
        """Simulate wind output (more erratic)."""
        import math
        wind_factor = max(0, math.sin(self.time_idx / 100) + np.random.normal(0, 0.3))
        return max(0, self.capacity_kw * min(1, wind_factor))
    
    def _generate_load_reading(self) -> float:
        """Simulate household load (baseline + peaks)."""
        import math
        hour_of_day = (self.time_idx % 86400) / 3600
        # Higher load in evening (17-21)
        peak_hours = max(0, 1 - abs(hour_of_day - 19) / 4)
        baseline = 0.5 * self.capacity_kw
        return baseline + peak_hours * 0.5 * self.capacity_kw
```

### Update `backend/src/streaming/communication.py`:

```python
def kafka_consume_centralized():
    """Consume device_readings topic and route to DB by source_type + community_id."""
    consumer = KafkaConsumer(
        "device_readings",
        bootstrap_servers='kafka:29092',
        auto_offset_reset='earliest',
        group_id='community-consumer',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    db_manager = DatabaseManager()
    crud = CrudManager(db_manager)
    
    for msg in consumer:
        data = msg.value
        device_type = data['device_type']  # solar, wind, load
        source_id = data['source_id']
        community_id = data['community_id']
        value = data['value']
        timestamp = data['timestamp']
        
        # Route to correct table
        if device_type in ['solar', 'wind']:
            query = f"INSERT INTO {device_type} (time, source_id, value, community_id) VALUES (%s, %s, %s, %s)"
            db_manager.execute(query, (timestamp, source_id, value, community_id))
        elif device_type == 'load':
            query = "INSERT INTO load (time, source_id, value, community_id) VALUES (%s, %s, %s, %s)"
            db_manager.execute(query, (timestamp, source_id, value, community_id))
        # market is separate, handled elsewhere
```

### Device simulator registry (`backend/src/streaming/simulator_manager.py`):

```python
class SimulatorManager:
    """Manage active device simulators (start/stop per source)."""
    
    _simulators = {}  # {source_id: asyncio.Task}
    
    @classmethod
    async def start_simulator(cls, source_id: str, source_type: str, 
                              community_id: str, latitude: float, longitude: float):
        if source_id in cls._simulators:
            return  # Already running
        
        sim = DeviceSimulator(source_id, source_type, community_id, latitude, longitude)
        task = asyncio.create_task(sim.run())
        cls._simulators[source_id] = (sim, task)
    
    @classmethod
    async def stop_simulator(cls, source_id: str):
        if source_id in cls._simulators:
            sim, task = cls._simulators.pop(source_id)
            sim.stop()
            await task
```

---

## F. Backend Startup: Resume Active Devices

### Update `backend/api/main.py`:

```python
import asyncio

@app.on_event("startup")
async def startup_simulators():
    """On startup, resume all active devices for all communities."""
    db = DatabaseManager()
    
    # Query all active sources
    sources = db.execute(
        """SELECT source_id, type, community_id, latitude, longitude 
           FROM energy_sources WHERE active = TRUE""",
        fetch=True
    )
    
    from backend.src.streaming.simulator_manager import SimulatorManager
    for source_id, source_type, community_id, lat, lon in sources:
        await SimulatorManager.start_simulator(source_id, source_type, community_id, lat, lon)
        print(f"Resumed simulator for {source_id}")
```

---

## G. Wipe & Reset Strategy

### New script: `scripts/reset_for_phase1.sql`

```sql
-- Wipe all data (start fresh)
DELETE FROM solar;
DELETE FROM wind;
DELETE FROM load;
DELETE FROM market;
DELETE FROM solar_forecast;
DELETE FROM wind_forecast;
DELETE FROM load_forecast;
DELETE FROM energy_sources;
DELETE FROM households;
DELETE FROM batteries;
DELETE FROM communities;
DELETE FROM electric_vehicles;

-- Run migrations to add community_id columns
-- (will be run via Python migration script)
```

Run on startup (optional, only in dev):
```python
if os.getenv("RESET_DB") == "true":
    run_script("scripts/reset_for_phase1.sql")
```

---

## H. Testing Strategy

### New test file: `tests/test_communities.py`
- Create community ✓
- List communities ✓
- Add source to community ✓
- Verify community isolation (user A can't see user B's community) ✓

### Update existing tests:
- All source/household/battery tests now require `community_id`
- All must verify access control (manager-only)

---

## I. Implementation Order

1. **Schema** — run migrations, add `community_id` columns
2. **Models** — add Pydantic `Community`, update others with `community_id`
3. **Routes** — implement `/api/communities`, update `/api/sources` / `/api/households` / `/api/batteries`
4. **Streaming** — build `DeviceSimulator`, `SimulatorManager`, update consumer
5. **Startup** — auto-resume devices on backend startup
6. **Tests** — write community tests, verify isolation
7. **Frontend** (Phase 2) — community selector, adjusted dashboards

---

## J. Files to Create / Modify

### Create:
- `backend/api/routes/communities.py`
- `backend/src/streaming/device_simulator.py`
- `backend/src/streaming/simulator_manager.py`
- `backend/src/db/migrations/001_add_community_id.sql`
- `tests/test_communities.py`
- `scripts/reset_for_phase1.sql`

### Modify:
- `backend/api/main.py` (add communities router, startup hook)
- `backend/api/models.py` (add Community models, update existing with community_id)
- `backend/api/routes/sources.py`, `households.py`, `batteries.py` (add community_id, verify access)
- `backend/src/streaming/communication.py` (consumer routes by device_type + community_id)
- `backend/src/db/schema.py` (migrations on startup)

---

## Architecture Decisions

### Key choices:
1. **Wipe & restart** — Start fresh DB, no migration of existing demo data
2. **One manager, many communities** — Supports scaling to multi-manager later
3. **Household = Prosumer** — Simplified model, no separate Prosumer entity
4. **Real-time simulation** — One reading per second (1s wall-clock = 1s simulated)
5. **Empty on creation** — Communities start with no data, users build as needed
6. **Auto-resume devices** — Backend startup queries active sources and resumes their simulators
7. **Single Kafka topic** — `device_readings` with routing by device_type + community_id

---

## Notes

- Market data remains **GLOBAL** (no community_id, shared across all)
- `load` data now has `source_id` (ties to a household/prosumer) and `community_id`
- Device simulator uses asyncio for concurrency (one per active source)
- Kafka producer/consumer both use `kafka:29092` (internal Docker bootstrap)
- All timestamps in ISO format with Z suffix (UTC)
