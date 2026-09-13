#!/usr/bin/env python3
"""Bootstrap: load a research community pack into the database.

Usage:
    python -m backend.src.research.load_pack --pack 50_1
    python -m backend.src.research.load_pack --pack 300_3

The script:
  1. Loads entity metadata from entities.json.
  2. Bulk-inserts households, sources, vehicles, battery, community.
  3. Bulk-inserts readings into solar / household_load hypertables.

Requires: database must already have the schema migrated
  (community_id column present on scoped tables).
"""

import argparse
import csv
import json
import sys
from contextlib import closing
from pathlib import Path

from psycopg2.extras import execute_values

from backend.src.db import DatabaseManager

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "packs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_column(db: DatabaseManager, table: str, column: str) -> bool:
    """Check whether *column* exists in *table*."""
    row = db.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s "
        "LIMIT 1",
        (table, column),
        fetch=True,
    )
    return bool(row)


def _bulk_insert(
    db: DatabaseManager,
    table: str,
    columns: list[str],
    rows: list[tuple],
):
    """Bulk-insert *rows* into *table* using execute_values."""
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES %s"
    with closing(db.connect()) as conn, conn, conn.cursor() as cursor:
        execute_values(cursor, sql, rows, page_size=1000)


# ---------------------------------------------------------------------------
# Entity loading
# ---------------------------------------------------------------------------

# Placeholder coordinates (Brussels): Fluvius data has no geolocation.
_PLACEHOLDER_LAT, _PLACEHOLDER_LON = 50.85, 4.35


def _insert_with_community(db: DatabaseManager, table: str, columns: list[str], rows: list[tuple], community_ids: list):
    """Bulk-insert rows, adding each row's community_id when the table has that column."""
    if not rows:
        return
    if _has_column(db, table, "community_id"):
        columns = [*columns, "community_id"]
        rows = [row + (community_id,) for row, community_id in zip(rows, community_ids)]
    _bulk_insert(db, table, columns, rows)


def _insert_households(db: DatabaseManager, households: list[dict]):
    columns = ["household_id", "name", "latitude", "longitude", "solar_panels", "building_type", "num_people", "num_evs"]
    rows = [
        (hh["household_id"], f"Household {hh['ean_id']}", _PLACEHOLDER_LAT, _PLACEHOLDER_LON,
         hh["solar_panels"], hh["building_type"], hh["num_people"], hh["num_evs"])
        for hh in households
    ]
    _insert_with_community(db, "households", columns, rows, [hh["community_id"] for hh in households])


def _insert_sources(db: DatabaseManager, sources: list[dict]):
    columns = ["source_id", "type", "latitude", "longitude", "household_id"]
    rows = [(src["source_id"], src["type"], _PLACEHOLDER_LAT, _PLACEHOLDER_LON, src["household_id"]) for src in sources]
    _insert_with_community(db, "energy_sources", columns, rows, [src["community_id"] for src in sources])


def _insert_vehicles(db: DatabaseManager, vehicles: list[dict]):
    columns = ["vehicle_id", "household_id", "name", "capacity_kwh", "soc_kwh", "max_charge_kw", "max_discharge_kw", "eta", "status"]
    rows = [tuple(v[c] for c in columns) for v in vehicles]
    if rows:
        _bulk_insert(db, "electric_vehicles", columns, rows)


def _insert_community_battery(db: DatabaseManager, entities: dict):
    """One shared battery per community, attached to the first household (FK required)."""
    capacity = entities["battery_capacity_kwh"]
    columns = ["battery_id", "household_id", "name", "capacity_kwh", "soc_kwh", "max_charge_kw", "max_discharge_kw", "eta"]
    row = (
        entities["battery_id"],
        entities["households"][0]["household_id"],
        f"Community battery ({entities['size']} HH)",
        capacity,
        capacity * entities["battery_soc_pct"],
        capacity * 0.2,  # 20 % of capacity as max charge
        capacity * 0.2,  # 20 % of capacity as max discharge
        0.95,
    )
    _insert_with_community(db, "batteries", columns, [row], [entities["community_id"]])


def load_pack(pack_name: str):
    """Load a single community pack into the database."""
    pack_dir = OUTPUT_DIR / pack_name
    if not pack_dir.joinpath("entities.json").exists():
        print(f"ERROR: Pack not found: {pack_dir}")
        sys.exit(1)

    print(f"Loading pack '{pack_name}' …")

    with open(pack_dir / "entities.json") as f:
        entities = json.load(f)

    db = DatabaseManager()
    community_id = entities["community_id"]

    print("  [1/4] Creating community …")
    db.execute("INSERT INTO communities (community_id, name) VALUES (%s, %s)", (community_id, entities["community_name"]))

    print("  [2/4] Inserting households …")
    _insert_households(db, entities["households"])

    print("  [3/4] Inserting sources …")
    _insert_sources(db, entities["sources"])

    print("  [4/4] Inserting vehicles …")
    _insert_vehicles(db, entities["vehicles"])

    print("  Inserting community battery …")
    _insert_community_battery(db, entities)

    print("\n  Loading readings …")
    readings_path = pack_dir / "readings.csv"
    if not readings_path.exists():
        print("  (no readings.csv found, skipping)")
    else:
        _load_readings(db, readings_path, community_id)

    print(f"\n  ✓ Pack '{pack_name}' loaded successfully.")
    print(f"    {len(entities['households'])} households")
    print(f"    {len(entities['sources'])} solar sources")
    print(f"    {len(entities['vehicles'])} electric vehicles")


def _load_readings(db: DatabaseManager, path: Path, community_id: str):
    """Bulk-insert readings.csv into the appropriate hypertables."""
    has_community_solar = _has_column(db, "solar", "community_id")
    has_community_load = _has_column(db, "household_load", "community_id")

    solar_cols = ["time", "source_id", "value"]
    if has_community_solar:
        solar_cols.append("community_id")

    load_cols = ["time", "household_id", "value"]
    if has_community_load:
        load_cols.append("community_id")

    # Values for the optional community_id column, appended to every row.
    solar_extra = (community_id,) if has_community_solar else ()
    load_extra = (community_id,) if has_community_load else ()

    chunk_size = 5000
    solar_rows: list[tuple] = []
    load_rows: list[tuple] = []
    n_solar = 0
    n_load = 0

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row["timestamp"]
            value = float(row["value"])
            meter_type = row["meter_type"]

            if meter_type == "solar":
                row_tuple = (ts, row["source_id"], value, *solar_extra)
                solar_rows.append(row_tuple)
                n_solar += 1
            else:
                row_tuple = (ts, row["household_id"], value, *load_extra)
                load_rows.append(row_tuple)
                n_load += 1

            if len(solar_rows) >= chunk_size:
                _bulk_insert(db, "solar", solar_cols, solar_rows)
                solar_rows = []
            if len(load_rows) >= chunk_size:
                _bulk_insert(db, "household_load", load_cols, load_rows)
                load_rows = []

        # Final flush
        if solar_rows:
            _bulk_insert(db, "solar", solar_cols, solar_rows)
        if load_rows:
            _bulk_insert(db, "household_load", load_cols, load_rows)

    print(f"  → {n_solar + n_load:,} readings inserted "
          f"({n_solar:,} solar + {n_load:,} load)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Load a research community pack into the database.",
    )
    parser.add_argument(
        "--pack",
        required=True,
        help="Pack name, e.g. '50_1' for size=50 seed=1.",
    )
    args = parser.parse_args()
    load_pack(args.pack)


if __name__ == "__main__":
    main()
