# Implementation Plan — Missing Features

This document describes how to implement each feature from `MISSING_FEATURES.md`, grounded in the existing codebase architecture.

---

## Dependency Graph (build order)

```
1. Stationary Batteries          (no deps — foundational asset type)
2. Wind Source Completion         (no deps — completes existing skeleton)
3. Real Tariff Structures         (no deps — new table + optimizer change)
4. Grid Export Limits             (depends on 3 — optimizer constraint)
5. P2P Energy Sharing             (depends on 1, 3 — core community feature)
6. Cost Tracking & Billing        (depends on 3, 5 — settlement engine)
7. Demand Response                (depends on 3 — flexible loads in optimizer)
8. Real Weather Integration       (no deps — replaces synthetic fallback)
9. Historical Analytics           (depends on 6 — needs cost data to be meaningful)
10. Alerts & Notifications        (depends on 5, 6 — trigger on events)
```

---

## 1. Stationary Batteries

**Problem:** `battery.py` was deleted. EVs are the only storage, but they disappear when status="away". Real communities have home batteries (Powerwall, etc.) that are always available.

### Database

New table in `schema.py`:

```sql
CREATE TABLE IF NOT EXISTS batteries (
    battery_id   VARCHAR(50) PRIMARY KEY,
    household_id VARCHAR(50) NOT NULL REFERENCES households(household_id) ON DELETE CASCADE,
    name         VARCHAR(100),
    capacity_kwh DOUBLE PRECISION CHECK (capacity_kwh > 0),
    soc_kwh      DOUBLE PRECISION CHECK (soc_kwh >= 0),
    max_charge_kw    DOUBLE PRECISION CHECK (max_charge_kw > 0),
    max_discharge_kw DOUBLE PRECISION CHECK (max_discharge_kw > 0),
    eta          DOUBLE PRECISION CHECK (eta > 0 AND eta <= 1) DEFAULT 0.95,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### API

New route file `backend/api/routes/batteries.py`, mirroring `vehicles.py`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/batteries` | GET | List user's batteries |
| `/batteries` | POST | Create battery (linked to household) |
| `/batteries/{id}` | GET | Get single battery |
| `/batteries/{id}` | DELETE | Delete battery |
| `/batteries/{id}/charge` | POST | Charge (same logic as EV) |
| `/batteries/{id}/discharge` | POST | Discharge |

### Optimization

Modify `optimization.py`:
- Currently iterates over `ev_specs` from `get_home_evs()`.
- Add `get_home_batteries(user_id)` to CRUD — returns all batteries (they're always "home").
- In `optimize()`, combine EVs (status="home") + all batteries into a single `storage_assets` list.
- The PuLP model already treats them generically (charge/discharge/SOC per asset) — just extend the input list.

### Community Summary

Add to `get_community_summary()`:
```python
battery_query = """
SELECT COALESCE(SUM(b.soc_kwh), 0), COALESCE(SUM(b.capacity_kwh), 0), COUNT(*)
FROM batteries b
JOIN households hh ON b.household_id = hh.household_id
WHERE hh.user_id = %s
"""
```
Return `battery_soc_total`, `battery_capacity`, `battery_count` alongside EV fields.

### Effort: Small — mirrors EV implementation.

---

## 2. Wind Source Completion

**Problem:** `create_new_source()` in `sources.py` raises `ValueError` for anything other than `"solar"`. The schema supports wind, the consumer listens to the `"wind"` Kafka topic, but there's no wind producer.

### Streaming

In `backend/src/streaming/sources.py`, add wind branch:

```python
elif source_type == "wind":
    weather_data = generate_weather_data(lat, lon, num_days, starting_date, source_id)
    wind_df = generate_wind_data(weather_data, lat, lon, source_id)
    # generate_wind_data uses windpowerlib (already in requirements)
```

### Data Generation

New function in `generation.py`:

```python
def generate_wind_data(weather_data, latitude, longitude, source_id):
    """Use windpowerlib to simulate a small wind turbine."""
    from windpowerlib import ModelChain, WindTurbine
    turbine = WindTurbine(
        hub_height=50,
        rotor_diameter=20,
        nominal_power=50000,  # 50 kW small turbine
    )
    mc = ModelChain(turbine)
    mc.run_model(weather_data)
    return mc.power_output
```

### Schema

Already exists — `wind` table has same structure as `solar`. `energy_sources.type` CHECK constraint needs updating to allow `'wind'`:

```sql
ALTER TABLE energy_sources DROP CONSTRAINT IF EXISTS energy_sources_type_check;
ALTER TABLE energy_sources ADD CONSTRAINT energy_sources_type_check CHECK (type IN ('solar', 'wind'));
```

### Community Summary

Update production query to include wind:
```sql
-- Add wind production alongside solar
SELECT COALESCE(SUM(latest.value), 0) FROM (
    SELECT DISTINCT ON (w.source_id) w.value
    FROM wind w JOIN energy_sources es ON w.source_id = es.source_id
    WHERE es.user_id = %s
    ORDER BY w.source_id, w.time DESC
) latest
```

Set `total_production = total_solar + total_wind`.

### Effort: Small-Medium — pvlib pattern exists, replicate for windpowerlib.

---

## 3. Real Tariff Structures

**Problem:** Market prices are synthetic sine waves (~$50 ± $20/MWh). No TOU pricing, no feed-in tariffs, no demand charges.

### Database

```sql
CREATE TABLE IF NOT EXISTS tariffs (
    tariff_id    VARCHAR(50) PRIMARY KEY,
    name         VARCHAR(100),
    tariff_type  VARCHAR(20) CHECK (tariff_type IN ('grid_import', 'grid_export', 'demand')),
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tariff_periods (
    tariff_id    VARCHAR(50) REFERENCES tariffs(tariff_id) ON DELETE CASCADE,
    day_type     VARCHAR(10) CHECK (day_type IN ('weekday', 'weekend', 'all')),
    hour_start   INT CHECK (hour_start >= 0 AND hour_start < 24),
    hour_end     INT CHECK (hour_end > 0 AND hour_end <= 24),
    price_per_kwh DOUBLE PRECISION,
    PRIMARY KEY (tariff_id, day_type, hour_start)
);
```

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tariffs` | GET | List available tariffs |
| `/tariffs` | POST | Create tariff with periods |
| `/tariffs/{id}` | DELETE | Remove tariff |
| `/tariffs/active` | GET | Get the community's active tariff |
| `/tariffs/{id}/activate` | POST | Set as active tariff |

### Optimization

Replace the flat `market_forecast` price vector with TOU-aware pricing:

```python
# Current (line ~35 of optimization.py):
market_prices = crud.load_forecasted_data("market", ...)

# New:
import_prices = tariff_engine.get_prices("grid_import", timestamps)
export_prices = tariff_engine.get_prices("grid_export", timestamps)

# Objective becomes:
prob += lpSum(
    import_prices[t] * grid_buy[t] - export_prices[t] * grid_sell[t]
    for t in range(T)
)
```

This changes the objective from a single price to separate buy/sell prices — a critical improvement.

### Effort: Medium — new tables, tariff engine, optimizer refactor.

---

## 4. Grid Export Limits

**Problem:** The optimizer has no cap on `grid_sell[t]`. Real grid connections have max export capacity (e.g., 10 kW per household, 50 kW per community).

### Database

Add column to a community/settings table (or per-household):

```sql
ALTER TABLE households ADD COLUMN grid_export_limit_kw DOUBLE PRECISION DEFAULT NULL;
```

Or a community-level setting:
```sql
CREATE TABLE IF NOT EXISTS community_settings (
    key   VARCHAR(50) PRIMARY KEY,
    value TEXT
);
-- INSERT INTO community_settings VALUES ('grid_export_limit_kw', '50');
```

### Optimization

One line in `optimization.py`:

```python
# After grid_sell variable creation:
for t in range(T):
    prob += grid_sell[t] <= grid_export_limit, f"export_cap_{t}"
```

### Effort: Tiny — one constraint + one setting.

---

## 5. Peer-to-Peer Energy Sharing

**Problem:** The system calculates net production/consumption per user but has no mechanism to redistribute surplus between households. This is the core value prop.

### Sharing Models

Support two common models:

**a) Proportional sharing (simplest):** Surplus is split proportionally to each household's consumption share.

**b) Priority-based:** Households with batteries/EVs get surplus first (incentivizes storage investment).

### Database

```sql
CREATE TABLE IF NOT EXISTS sharing_rules (
    rule_id      VARCHAR(50) PRIMARY KEY,
    community_id VARCHAR(50),  -- future multi-community support
    rule_type    VARCHAR(20) CHECK (rule_type IN ('proportional', 'priority', 'fixed')),
    params       JSONB DEFAULT '{}',
    active       BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS energy_transactions (
    transaction_id SERIAL PRIMARY KEY,
    time           TIMESTAMPTZ NOT NULL,
    from_household VARCHAR(50) REFERENCES households(household_id),
    to_household   VARCHAR(50) REFERENCES households(household_id),
    energy_kwh     DOUBLE PRECISION,
    price_per_kwh  DOUBLE PRECISION,
    transaction_type VARCHAR(20) CHECK (transaction_type IN ('p2p', 'grid_import', 'grid_export')),
    created_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
SELECT create_hypertable('energy_transactions', 'time', if_not_exists => TRUE);
```

### Settlement Engine

New module `backend/src/settlement/engine.py`:

```python
def settle_interval(crud, user_id, timestamp):
    """Run settlement for one time interval."""
    households = crud.get_all_households(user_id=user_id)

    producers = []  # households with net surplus
    consumers = []  # households with net deficit

    for hh in households:
        production = get_household_production(crud, hh["household_id"], timestamp)
        consumption = get_household_consumption(crud, hh["household_id"], timestamp)
        net = production - consumption
        if net > 0:
            producers.append((hh, net))
        else:
            consumers.append((hh, abs(net)))

    total_surplus = sum(p[1] for p in producers)
    total_deficit = sum(c[1] for c in consumers)

    # Proportional sharing: each consumer gets share of surplus
    shareable = min(total_surplus, total_deficit)

    transactions = []
    for consumer_hh, deficit in consumers:
        consumer_share = (deficit / total_deficit) * shareable if total_deficit > 0 else 0
        # Allocate from producers proportionally
        for producer_hh, surplus in producers:
            producer_share = (surplus / total_surplus) * consumer_share if total_surplus > 0 else 0
            if producer_share > 0:
                transactions.append({
                    "from_household": producer_hh["household_id"],
                    "to_household": consumer_hh["household_id"],
                    "energy_kwh": producer_share,
                    "price_per_kwh": community_tariff,  # from tariff table
                    "transaction_type": "p2p",
                })

    # Remaining deficit → grid import, remaining surplus → grid export
    ...

    return transactions
```

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/community/sharing-rules` | GET/POST | Manage sharing rules |
| `/community/transactions` | GET | View energy transactions (filterable by household, date range) |
| `/community/settle` | POST | Trigger settlement for a time range |
| `/households/{id}/energy-balance` | GET | Per-household production/consumption/P2P breakdown |

### Optimization Integration

The optimizer should become community-aware:
- Instead of one `grid_buy`/`grid_sell`, model per-household flows.
- Internal transfers between households are free or at community rate.
- Only the community-level net goes to grid.

This is a significant optimizer refactor — move from single-node to multi-node optimization:

```python
# Per-household variables:
household_net[hh, t]  # net production for household hh at time t
p2p_send[hh1, hh2, t]  # energy from hh1 to hh2
p2p_receive[hh1, hh2, t]

# Community-level:
community_grid_buy[t]  = sum of remaining deficits
community_grid_sell[t]  = sum of remaining surpluses
```

### Effort: Large — this is the biggest feature. Start with proportional sharing without optimizer integration, then add optimizer-aware P2P.

---

## 6. Cost Tracking & Billing

**Problem:** No per-household cost/savings. Members can't see "you saved X this month."

### Database

```sql
CREATE TABLE IF NOT EXISTS billing_records (
    record_id    SERIAL PRIMARY KEY,
    household_id VARCHAR(50) REFERENCES households(household_id) ON DELETE CASCADE,
    period_start TIMESTAMPTZ,
    period_end   TIMESTAMPTZ,
    grid_import_kwh   DOUBLE PRECISION DEFAULT 0,
    grid_import_cost  DOUBLE PRECISION DEFAULT 0,
    grid_export_kwh   DOUBLE PRECISION DEFAULT 0,
    grid_export_revenue DOUBLE PRECISION DEFAULT 0,
    p2p_bought_kwh    DOUBLE PRECISION DEFAULT 0,
    p2p_bought_cost   DOUBLE PRECISION DEFAULT 0,
    p2p_sold_kwh      DOUBLE PRECISION DEFAULT 0,
    p2p_sold_revenue  DOUBLE PRECISION DEFAULT 0,
    net_cost           DOUBLE PRECISION DEFAULT 0,  -- total bill
    baseline_cost      DOUBLE PRECISION DEFAULT 0,  -- what they'd pay without community
    savings            DOUBLE PRECISION DEFAULT 0,  -- baseline - net_cost
    created_at         TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (household_id, period_start)
);
```

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/billing/current` | GET | Current period costs for all households |
| `/billing/history` | GET | Historical billing records (monthly) |
| `/billing/{household_id}` | GET | Single household billing detail |
| `/billing/generate` | POST | Generate billing for a period (runs settlement) |
| `/community/savings` | GET | Community-wide savings summary |

### Computation

```python
def compute_billing(crud, household_id, period_start, period_end, tariff):
    transactions = crud.get_transactions(household_id, period_start, period_end)

    grid_import = sum(t["energy_kwh"] for t in transactions if t["type"] == "grid_import")
    grid_export = sum(t["energy_kwh"] for t in transactions if t["type"] == "grid_export")
    p2p_bought = sum(t["energy_kwh"] for t in transactions if t["type"] == "p2p" and t["to"] == household_id)
    p2p_sold = sum(t["energy_kwh"] for t in transactions if t["type"] == "p2p" and t["from"] == household_id)

    # Costs using tariff
    import_cost = sum(tariff.price_at(t["time"]) * t["energy_kwh"] for t in grid_imports)
    export_revenue = sum(tariff.export_price_at(t["time"]) * t["energy_kwh"] for t in grid_exports)
    p2p_cost = p2p_bought * community_rate
    p2p_revenue = p2p_sold * community_rate

    net_cost = import_cost + p2p_cost - export_revenue - p2p_revenue

    # Baseline: what they'd pay buying everything from grid
    total_consumption = grid_import + p2p_bought  # all energy consumed
    baseline_cost = total_consumption * avg_grid_rate

    savings = baseline_cost - net_cost
    return {...}
```

### Effort: Medium — depends on tariffs (3) and P2P (5) being implemented first.

---

## 7. Demand Response / Flexible Loads

**Problem:** Only storage is optimized. Shifting flexible loads (water heaters, dishwashers, EV charging schedules) is often the biggest cost saver.

### Database

```sql
CREATE TABLE IF NOT EXISTS flexible_loads (
    load_id      VARCHAR(50) PRIMARY KEY,
    household_id VARCHAR(50) REFERENCES households(household_id) ON DELETE CASCADE,
    name         VARCHAR(100),
    load_type    VARCHAR(30) CHECK (load_type IN ('water_heater', 'dishwasher', 'laundry', 'ev_charging', 'hvac', 'custom')),
    power_kw     DOUBLE PRECISION CHECK (power_kw > 0),
    duration_h   DOUBLE PRECISION CHECK (duration_h > 0),
    earliest_start INT CHECK (earliest_start >= 0 AND earliest_start < 24),  -- hour of day
    latest_end     INT CHECK (latest_end > 0 AND latest_end <= 24),
    must_run_daily BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### Optimization

Add flexible load scheduling to the PuLP model:

```python
# New binary variable: is load l running at time t?
load_active = {}
for load in flexible_loads:
    for t in range(T):
        load_active[(load.id, t)] = LpVariable(f"load_{load.id}_{t}", cat="Binary")

    # Must run for exactly `duration_h` hours
    prob += lpSum(load_active[(load.id, t)] for t in range(T)) == load.duration_h

    # Only within allowed window
    for t in range(T):
        hour = timestamps[t].hour
        if hour < load.earliest_start or hour >= load.latest_end:
            prob += load_active[(load.id, t)] == 0

# Update power balance:
# net_excess[t] = solar[t] - base_load[t] - flexible_load[t] + charge[t] - discharge[t]
flexible_load_t = lpSum(
    load.power_kw * load_active[(load.id, t)] for load in flexible_loads
)
```

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/flexible-loads` | GET/POST | CRUD for flexible loads |
| `/flexible-loads/{id}` | GET/DELETE | Manage individual loads |
| `/flexible-loads/{id}/schedule` | GET | Get optimized schedule for this load |

### Effort: Medium — optimizer gets more complex (mixed-integer) but PuLP/CBC handles it.

---

## 8. Real Weather Integration

**Problem:** Weather endpoint falls back to synthetic data. Forecasts should use actual weather.

### Implementation

In `backend/api/routes/weather.py`, the OpenWeatherMap integration already exists but falls back to synthetic. The fix:

1. **Store API key in `.env`**: `OPENWEATHERMAP_API_KEY=...`
2. **Use forecast API for production forecasting**: Replace synthetic GHI/DNI/DHI with forecast data in the inference pipeline.

```python
# backend/src/pipelines/weather_fetcher.py
def fetch_solar_irradiance_forecast(lat, lon, api_key):
    """Fetch from Open-Meteo (free, no key needed) or OpenWeatherMap."""
    # Open-Meteo is free and provides GHI, DNI, DHI forecasts
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    url += "&hourly=direct_normal_irradiance,diffuse_radiation,global_tilted_irradiance"
    url += "&forecast_days=7"
    response = requests.get(url)
    return response.json()
```

### Integration Points

- **Inference pipeline**: Before running ML forecasts, fetch latest weather forecast and use as features.
- **Source creation**: Use real irradiance instead of synthetic sine waves for new source data (when available).
- **Dashboard**: Show current weather conditions affecting production.

### Effort: Small — Open-Meteo is free and provides exactly what pvlib needs.

---

## 9. Historical Analytics & Reports

**Problem:** Community summary is a point-in-time snapshot. No trends, no comparisons.

### Database

Materialized views or periodic aggregation:

```sql
-- Hourly community snapshot (populated by a periodic job)
CREATE TABLE IF NOT EXISTS community_snapshots (
    time             TIMESTAMPTZ NOT NULL,
    total_production DOUBLE PRECISION,
    total_consumption DOUBLE PRECISION,
    net              DOUBLE PRECISION,
    ev_soc_total     DOUBLE PRECISION,
    battery_soc_total DOUBLE PRECISION,
    grid_import_kwh  DOUBLE PRECISION,
    grid_export_kwh  DOUBLE PRECISION,
    household_count  INT,
    created_at       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
SELECT create_hypertable('community_snapshots', 'time', if_not_exists => TRUE);
```

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/analytics/community/timeseries` | GET | Community metrics over time (params: start, end, resolution) |
| `/analytics/community/summary` | GET | Aggregated stats for a period (daily/weekly/monthly) |
| `/analytics/household/{id}/timeseries` | GET | Per-household metrics over time |
| `/analytics/forecast-accuracy` | GET | Compare forecast vs actual (MAE, MAPE) |
| `/analytics/self-sufficiency` | GET | % of consumption met by own production over time |

### Key Metrics to Track

- **Self-sufficiency ratio**: production / consumption (per household, per community)
- **Self-consumption ratio**: locally consumed production / total production
- **Peak demand reduction**: comparing peak with/without optimization
- **Forecast accuracy**: yhat vs actual for solar, load, market
- **Savings trend**: monthly savings compared to grid-only baseline

### Frontend

New `Analytics.tsx` page with:
- Time-series charts (production vs consumption over days/weeks)
- Bar charts (monthly costs, savings)
- Comparison cards (this month vs last month)
- Forecast accuracy gauges

### Effort: Medium — mostly new queries and a new frontend page.

---

## 10. Alerts & Notifications

**Problem:** No proactive communication. Users discover issues only by checking the dashboard.

### Database

```sql
CREATE TABLE IF NOT EXISTS alerts (
    alert_id     SERIAL PRIMARY KEY,
    user_id      VARCHAR(50) REFERENCES users(user_id) ON DELETE CASCADE,
    household_id VARCHAR(50) REFERENCES households(household_id) ON DELETE SET NULL,
    alert_type   VARCHAR(30),  -- 'production_drop', 'price_spike', 'battery_low', 'forecast_error'
    severity     VARCHAR(10) CHECK (severity IN ('info', 'warning', 'critical')),
    message      TEXT,
    acknowledged BOOLEAN DEFAULT false,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id      VARCHAR(50) PRIMARY KEY,
    user_id      VARCHAR(50) REFERENCES users(user_id) ON DELETE CASCADE,
    rule_type    VARCHAR(30),
    threshold    DOUBLE PRECISION,
    enabled      BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### Alert Engine

New module `backend/src/alerts/engine.py`:

```python
ALERT_CHECKS = [
    {
        "type": "production_drop",
        "check": lambda current, avg: current < avg * 0.5,
        "message": "Solar production dropped below 50% of average",
        "severity": "warning",
    },
    {
        "type": "battery_low",
        "check": lambda soc, capacity: soc < capacity * 0.1,
        "message": "Battery below 10%",
        "severity": "info",
    },
    {
        "type": "price_spike",
        "check": lambda price, avg: price > avg * 2.0,
        "message": "Grid price spiked above 2x average — consider discharging batteries",
        "severity": "warning",
    },
    {
        "type": "negative_net",
        "check": lambda net, threshold: net < -threshold,
        "message": "Community is buying significant grid power",
        "severity": "info",
    },
]
```

### Delivery

- **In-app**: `GET /alerts` endpoint, polling from frontend.
- **WebSocket (future)**: Push via `backend/api/routes/ws.py` using FastAPI WebSocket.
- **Email (future)**: Queue alerts for email delivery.

### API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/alerts` | GET | List user's alerts (params: unread_only, severity) |
| `/alerts/{id}/acknowledge` | POST | Mark alert as read |
| `/alerts/rules` | GET/POST | Manage alert thresholds |

### Effort: Medium — alert engine + periodic check job + frontend notification bell.

---

---

## Generalisation TODOs

The current implementation targets **Belgium** specifically. The following items are hard-coded or Belgium-specific and should be generalised later:

- [ ] **Tariff structures**: Default tariffs use Belgian grid rates (Fluvius distribution tariffs, capacity tariff, prosumer tariff). Generalise to configurable per-country tariff templates.
- [ ] **P2P sharing model**: Only proportional sharing implemented. Add priority-based and fixed-allocation models as alternatives.
- [ ] **Multi-community**: Current model is single-community-per-user. Generalise to support multiple communities with a `communities` table and `community_id` foreign keys.
- [ ] **Grid export limits**: Belgian default (max 5 kVA for single-phase residential). Make configurable per country/connection type.
- [ ] **Feed-in tariff**: Belgian prosumer tariff / injection tariff. Other countries have different FIT schemes.
- [ ] **Regulatory reporting**: Belgian energy community reporting (Flemish Energy Regulator / VREG). Generalise to other EU regulators.
- [ ] **Currency**: Hard-coded EUR. Add currency field to community settings.
- [ ] **Wind turbine specs**: Default is a small community turbine typical for Belgian regulations. Other markets allow different sizes.

---

## Implementation Phases

### Phase 1: Foundation (weeks 1-3)
- **Stationary batteries** (1) — small, high value
- **Wind sources** (2) — completes existing skeleton
- **Grid export limits** (4) — tiny change, big realism gain
- **Real weather** (8) — small, improves data quality

### Phase 2: Economics (weeks 4-7)
- **Tariff structures** (3) — prerequisite for cost features
- **P2P energy sharing** (5) — core community feature, start with proportional model
- **Cost tracking** (6) — depends on 3 + 5

### Phase 3: Intelligence (weeks 8-10)
- **Demand response** (7) — optimizer enhancement
- **Historical analytics** (9) — new frontend page
- **Alerts** (10) — proactive UX

### Phase 4: Polish
- Mobile-responsive frontend
- Multi-community support
- Smart meter integration protocols
- Regulatory reporting templates
