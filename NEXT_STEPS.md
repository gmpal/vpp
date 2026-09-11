# Next Steps — Phase 1 Continuation

## Current State

**Branch:** `feature/phase1-community-entity`  
**Status:** Phase 1 backend complete, all 55 unit tests passing  
**Last commit:** `feat(startup): auto-resume simulators on backend start + wire start/stop on source CRUD`

---

## What Phase 1 Delivered (Done)

1. **Schema** — `communities` table + `community_id` columns on households, energy_sources, batteries, solar, wind, load, forecast hypertables
2. **Community CRUD** — `POST /api/communities`, `GET /api/communities`, `GET /api/communities/{id}` with manager-only access control
3. **Batteries route** — `POST/GET/DELETE/charge/discharge /api/batteries` (was missing, now fully implemented)
4. **Community scoping** — sources and households accept optional `community_id`, verified against ownership
5. **DeviceSimulator** — asyncio-based 1-reading/sec per source (solar/wind/load generation)
6. **SimulatorManager** — registry of running simulator tasks; start/stop/stop_all
7. **Consumer** — now subscribes to `device_readings` topic + legacy topics, routes by `device_type + community_id`
8. **Startup hook** — backend auto-resumes simulators for all sources with a `community_id` on startup

---

## Immediate Next Steps (Do These First)

### 1. Open PR for Phase 1 backend
```bash
git push origin feature/phase1-community-entity
gh pr create --title "feat: Phase 1 — Community entity + real-time device simulation" \
  --body "Implements IMPLEMENTATION_PLAN_PHASE1.md backend work"
```

### 2. DB reset script (from the plan)
- Create `scripts/reset_for_phase1.sql` as specified in section G of `IMPLEMENTATION_PLAN_PHASE1.md`
- Wire it to `RESET_DB=true` env var in `main.py` or `admin.py`

### 3. Integration tests for communities
File: `tests/test_db_integration.py` (already exists — extend it)  
Add:
- Create community in real DB, verify it's stored
- Create household scoped to community, verify FK
- Community isolation: user A cannot see user B's community (create two users, verify)

---

## Phase 2 — Frontend (Next Major Work)

Per `IMPLEMENTATION_PLAN_PHASE1.md` section I point 7.

### Files to create/modify:
- `frontend/src/CommunitySelector.tsx` — dropdown/list of user's communities
- `frontend/src/Dashboard.tsx` — pass selected `community_id` to all API calls
- `frontend/src/api.ts` — add `getCommunities()`, `createCommunity()`, update `addSource()`/`createHousehold()` to include `community_id`

### Key behavior:
1. On login → fetch communities list
2. If no community → prompt to create one first
3. All data creation (sources, households, batteries) passes the selected `community_id`
4. Dashboard shows data scoped to selected community only

---

## Known Limitations / Tech Debt

| Issue | Location | Notes |
|-------|----------|-------|
| `community_id` is optional on POST requests | `sources.py`, `households.py` | Plan says required; kept optional for backward compat. Make required after frontend update. |
| Simulators run in-process | `simulator_manager.py` | Memory grows with active sources. Acceptable for Phase 1 demo scale. |
| `load` table had no `source_id` before migration | `schema.py` | `_migrate_add_community_id()` adds `community_id` but `source_id` on load is not yet enforced. Consumer now writes `source_id` to load via device_readings. |
| `@app.on_event("startup")` deprecated | `main.py` | FastAPI recommends `lifespan` context manager. Non-breaking warning only. |
| `DeviceSimulator.wind` model is simple | `device_simulator.py` | Uses `sin(tick/100)` — replace with pvlib/windpowerlib for realism in later phase. |

---

## Test Coverage Summary

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_communities.py` | 10 | Community CRUD routes, 404/403 cases |
| `tests/test_batteries.py` | 13 | Battery CRUD routes, charge/discharge SOC math |
| `tests/test_households.py` | 11 | Household CRUD routes |
| `tests/test_device_simulator.py` | 20 | Generation logic, message format, manager lifecycle, consumer routing |
| `tests/test_api_unit.py` | 1 | Health check smoke test |

Run all: `python -m pytest tests/test_communities.py tests/test_households.py tests/test_batteries.py tests/test_api_unit.py tests/test_device_simulator.py`

---

## Files Changed in Phase 1

### Created
- `backend/api/routes/batteries.py`
- `backend/src/streaming/device_simulator.py`
- `backend/src/streaming/simulator_manager.py`
- `tests/test_communities.py`
- `tests/test_batteries.py`
- `tests/test_device_simulator.py`

### Modified
- `backend/api/main.py` — added batteries router, startup hooks
- `backend/api/models.py` — Community, CommunityCreate, Battery, BatteryCreate, BatteryOperation models
- `backend/api/routes/community.py` — expanded from summary-only to full CRUD
- `backend/api/routes/sources.py` — community_id verification, simulator start/stop
- `backend/api/routes/households.py` — community_id verification
- `backend/src/db/schema.py` — _create_communities_table(), _migrate_add_community_id()
- `backend/src/db/crud.py` — community CRUD methods, create_household gets community_id
- `backend/src/streaming/communication.py` — device_readings topic + _handle_device_reading()
- `tests/test_api_unit.py` — stripped to health check only (old in-memory tests removed)
- `tests/test_households.py` — fixed auth fixture pattern
