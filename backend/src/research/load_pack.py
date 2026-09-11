#!/usr/bin/env python3
"""Bootstrap: load a research community pack into the database.

Usage:
    python -m backend.src.research.load_pack --pack 50_1
    python -m backend.src.research.load_pack --pack 300_3

The script:
  1. Ensures a default admin user exists (idempotent).
  2. Loads entity metadata from entities.json.
  3. Bulk-inserts households, sources, vehicles, battery, community.
  4. Bulk-inserts readings into solar / household_load hypertables.

Requires: database must already have the schema migrated
  (community_id column present on scoped tables).
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import bcrypt
import pandas as pd

from backend.src.db import DatabaseManager
from psycopg2.extras import execute_values

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "packs"

# ---------------------------------------------------------------------------
# Admin user
# ---------------------------------------------------------------------------

ADMIN_USER_ID = "admin"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"  # pragma: allowlist secret — research only


def ensure_admin_user(db: DatabaseManager):
    """Create default admin user if it does not exist."""
    rows = db.execute(
        "SELECT 1 FROM users WHERE user_id = %s LIMIT 1",
        (ADMIN_USER_ID,),
        fetch=True,
    )
    if rows:
        print("  Admin user already exists.")
        return

    hashed = bcrypt.hashpw(
        ADMIN_PASSWORD.encode(),
        bcrypt.gensalt(),
    ).decode()

    db.execute(
        "INSERT INTO users (user_id, username, hashed_password) "
        "VALUES (%s, %s, %s)",
        (ADMIN_USER_ID, ADMIN_USERNAME, hashed),
    )
    print(f"  Created admin user '{ADMIN_USER_ID}'.")


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
    conn = db.connect()
    with conn:
        execute_values(conn, sql, rows, page_size=1000)


# ---------------------------------------------------------------------------
# Entity loading
# ---------------------------------------------------------------------------

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

    # --- 1. Admin user ---
    print("  [1/5] Ensuring admin user …")
    ensure_admin_user(db)

    # --- 2. Community ---
    print("  [2/5] Creating community …")
    community_id = entities["community_id"]
    db.execute(
        "INSERT INTO communities (community_id, manager_user_id, name) "
        "VALUES (%s, %s, %s)",
        (community_id, ADMIN_USER_ID, entities["community_name"]),
    )

    # --- 3. Households ---
    print("  [3/5] Inserting households …")
    has_community = _has_column(db, "households", "community_id")
    hh_cols = ["household_id", "name", "latitude", "longitude",
               "solar_panels", "building_type", "num_people", "num_evs"]
    if has_community:
        hh_cols.append("community_id")

    hh_rows = []
    for hh in entities["households"]:
        row = (
            hh["household_id"],
            f"Household {hh['ean_id']}",
            50.85,  # placeholder: Brussels (no geo in Fluvius)
            4.35,
            hh["solar_panels"],
            hh["building_type"],
            hh["num_people"],
            hh["num_evs"],
        )
        if has_community:
            row = row + (hh["community_id"],)
        hh_rows.append(row)

    _bulk_insert(db, "households", hh_cols, hh_rows)

    # --- 4. Energy sources (solar) ---
    print("  [4/5] Inserting sources …")
    has_community_src = _has_column(db, "energy_sources", "community_id")
    src_cols = ["source_id", "type", "latitude", "longitude",
                "household_id"]
    if has_community_src:
        src_cols.append("community_id")

    src_rows = []
    for src in entities["sources"]:
        row = (
            src["source_id"],
            src["type"],
            50.85,
            4.35,
            src["household_id"],
        )
        if has_community_src:
            row = row + (src["community_id"],)
        src_rows.append(row)

    if src_rows:
        _bulk_insert(db, "energy_sources", src_cols, src_rows)

    # --- 5. Electric vehicles ---
    print("  [5/5] Inserting vehicles …")
    veh_cols = ["vehicle_id", "household_id", "name",
                "capacity_kwh", "soc_kwh", "max_charge_kw",
                "max_discharge_kw", "eta", "status"]
    veh_rows = []
    for v in entities["vehicles"]:
        veh_rows.append((
            v["vehicle_id"], v["household_id"], v["name"],
            v["capacity_kwh"], v["soc_kwh"], v["max_charge_kw"],
            v["max_discharge_kw"], v["eta"], v["status"],
        ))

    if veh_rows:
        _bulk_insert(db, "electric_vehicles", veh_cols, veh_rows)

    # --- Battery (shared community) ---
    print("  Inserting community battery …")
    has_community_bat = _has_column(db, "batteries", "community_id")
    bat_cols = ["battery_id", "household_id", "name",
                "capacity_kwh", "soc_kwh", "max_charge_kw",
                "max_discharge_kw", "eta"]
    if has_community_bat:
        bat_cols.append("community_id")

    bat_rows = [(
        entities["battery_id"],
        entities["households"][0]["household_id"],  # FK to first HH (required)
        f"Community battery ({entities['size']} HH)",
        entities["battery_capacity_kwh"],
        entities["battery_capacity_kwh"] * entities["battery_soc_pct"],
        entities["battery_capacity_kwh"] * 0.2,   # 20 % of capacity as max charge
        entities["battery_capacity_kwh"] * 0.2,   # 20 % of capacity as max discharge
        0.95,
    )]
    if has_community_bat:
        bat_rows[0] = bat_rows[0] + (community_id,)

    _bulk_insert(db, "batteries", bat_cols, bat_rows)

    # --- 6. Readings ---
    print("\n  Loading readings …")
    readings_path = pack_dir / "readings.csv"
    if not readings_path.exists():
        print("  (no readings.csv found, skipping)")
    else:
        _load_readings(db, readings_path)

    print(f"\n  ✓ Pack '{pack_name}' loaded successfully.")
    print(f"    {len(entities['households'])} households")
    print(f"    {len(entities['sources'])} solar sources")
    print(f"    {len(entities['vehicles'])} electric vehicles")
    db.close()


def _load_readings(db: DatabaseManager, path: Path):
    """Bulk-insert readings.csv into the appropriate hypertables."""
    has_community_solar = _has_column(db, "solar", "community_id")
    has_community_load = _has_column(db, "household_load", "community_id")

    solar_cols = ["time", "source_id", "value"]
    if has_community_solar:
        solar_cols.append("community_id")

    load_cols = ["time", "household_id", "value"]
    if has_community_load:
        load_cols.append("community_id")

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
                row_tuple = (ts, row["source_id"], value)
                solar_rows.append(row_tuple)
                n_solar += 1
            else:
                row_tuple = (ts, row["household_id"], value)
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
