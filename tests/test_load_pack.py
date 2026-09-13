# tests/test_load_pack.py
"""Integration tests for research/load_pack.py — community pack bootstrap.

These tests verify:
  - Community, household, source, vehicle, battery loading
  - Readings bulk-insertion
  - Loading a pack twice is rejected without duplicating rows

Run:
    pytest tests/test_load_pack.py -v -m integration
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import psycopg2
import pytest


@pytest.fixture
def sample_pack_dir(tmp_path):
    """Create a minimal community pack structure in tmp_path.

    Returns (pack_dir, pack_name) where pack_name is like '8_1'.
    """
    pack_name = "8_1"
    pack_dir = tmp_path / "packs" / pack_name
    pack_dir.mkdir(parents=True)

    # Minimal entities.json
    entities = {
        "community_id": "c1234567-89ab-cdef-0123-456789abcdef",
        "community_name": "test_community",
        "size": 8,
        "seed": 1,
        "battery_id": "bat_8_1",
        "battery_capacity_kwh": 80.0,  # 8 × 10
        "battery_soc_pct": 0.50,
        "households": [
            {
                "household_id": "hh_8_1_100",
                "ean_id": 100,
                "building_type": "Residentieel",
                "num_people": 1,
                "solar_panels": 1,
                "num_evs": 0,
                "community_id": "c1234567-89ab-cdef-0123-456789abcdef",
            },
            {
                "household_id": "hh_8_1_200",
                "ean_id": 200,
                "building_type": "Residentieel",
                "num_people": 2,
                "solar_panels": 0,
                "num_evs": 1,
                "community_id": "c1234567-89ab-cdef-0123-456789abcdef",
            },
        ],
        "sources": [
            {
                "source_id": "src_8_1_100",
                "household_id": "hh_8_1_100",
                "community_id": "c1234567-89ab-cdef-0123-456789abcdef",
                "type": "solar",
                "ean_id": 100,
            },
        ],
        "vehicles": [
            {
                "vehicle_id": "veh_8_1_200",
                "household_id": "hh_8_1_200",
                "community_id": "c1234567-89ab-cdef-0123-456789abcdef",
                "name": "EV_200",
                "capacity_kwh": 60.0,
                "soc_kwh": 30.0,
                "max_charge_kw": 11.0,
                "max_discharge_kw": 0.0,  # charge-only, as build_packs emits
                "eta": 0.95,
                "status": "home",
            },
        ],
    }

    with open(pack_dir / "entities.json", "w") as f:
        json.dump(entities, f)

    # Minimal readings.csv
    readings_path = pack_dir / "readings.csv"
    rows = [
        ("timestamp", "source_id", "household_id", "value", "meter_type"),
        ("2024-01-01T00:00:00.000Z", "src_8_1_100", "", "0.5", "solar"),
        ("2024-01-01T01:00:00.000Z", "", "hh_8_1_100", "1.2", "load"),
        ("2024-01-01T00:00:00.000Z", "src_8_1_100", "", "0.3", "solar"),
        ("2024-01-01T02:00:00.000Z", "", "hh_8_1_200", "0.8", "load"),
    ]
    with open(readings_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return pack_dir, pack_name


PACK_COMMUNITY_ID = "c1234567-89ab-cdef-0123-456789abcdef"


@pytest.fixture
def loaded_pack(schema_manager, cleanup, sample_pack_dir):
    """Load the sample pack into a fresh schema; tables are emptied afterwards."""
    from backend.src.research.load_pack import load_pack

    pack_dir, pack_name = sample_pack_dir
    with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent):
        load_pack(pack_name)
    return pack_dir, pack_name


@pytest.mark.integration
class TestLoadPackEntities:
    """Test loading entity metadata."""

    def test_community_loaded(self, db_manager, loaded_pack):
        """Community should be created in the database."""
        rows = db_manager.execute(
            "SELECT community_id::text, name FROM communities WHERE community_id = %s",
            (PACK_COMMUNITY_ID,),
            fetch=True,
        )
        assert rows == [(PACK_COMMUNITY_ID, "test_community")]

    def test_households_loaded(self, db_manager, loaded_pack):
        """Households should be created with correct IDs."""
        rows = db_manager.execute(
            "SELECT household_id, solar_panels, num_evs, community_id::text "
            "FROM households WHERE household_id IN ('hh_8_1_100', 'hh_8_1_200') ORDER BY household_id",
            fetch=True,
        )
        assert rows == [
            ("hh_8_1_100", 1, 0, PACK_COMMUNITY_ID),
            ("hh_8_1_200", 0, 1, PACK_COMMUNITY_ID),
        ]

    def test_sources_loaded(self, db_manager, loaded_pack):
        """Solar sources should be created with correct household FK."""
        rows = db_manager.execute(
            "SELECT source_id, type, household_id FROM energy_sources "
            "WHERE source_id = 'src_8_1_100'",
            fetch=True,
        )
        assert rows == [("src_8_1_100", "solar", "hh_8_1_100")]

    def test_vehicles_loaded(self, db_manager, loaded_pack):
        """EV vehicles should be created with correct household FK."""
        rows = db_manager.execute(
            "SELECT vehicle_id, household_id, capacity_kwh, soc_kwh "
            "FROM electric_vehicles WHERE vehicle_id = 'veh_8_1_200'",
            fetch=True,
        )
        assert rows == [("veh_8_1_200", "hh_8_1_200", 60.0, 30.0)]

    def test_battery_loaded(self, db_manager, loaded_pack):
        """Community battery should be created with correct capacity."""
        rows = db_manager.execute(
            "SELECT battery_id, capacity_kwh, soc_kwh FROM batteries "
            "WHERE battery_id = 'bat_8_1'",
            fetch=True,
        )
        assert rows == [("bat_8_1", 80.0, 40.0)]  # 8 x 10 kWh, 50 % SOC


@pytest.mark.integration
class TestLoadPackReadings:
    """Test bulk-insertion of readings."""

    def test_readings_loaded(self, db_manager, loaded_pack):
        """Readings should be inserted into solar and household_load tables."""
        assert db_manager.execute("SELECT COUNT(*) FROM solar", fetch=True)[0][0] == 2
        assert db_manager.execute("SELECT COUNT(*) FROM household_load", fetch=True)[0][0] == 2
        rows = db_manager.execute("SELECT DISTINCT community_id::text FROM solar", fetch=True)
        assert rows == [(PACK_COMMUNITY_ID,)]

    def test_readings_timestamps_correct(self, db_manager, loaded_pack):
        """Timestamps should be correctly parsed and stored."""
        expected = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = db_manager.execute("SELECT time FROM solar ORDER BY time ASC", fetch=True)
        assert [r[0] for r in rows] == [expected, expected]
        rows = db_manager.execute("SELECT time FROM household_load ORDER BY time ASC", fetch=True)
        assert [r[0] for r in rows] == [expected.replace(hour=1), expected.replace(hour=2)]


@pytest.mark.integration
class TestLoadPackTwice:
    """load_pack uses plain INSERTs, so a pack can only be loaded once."""

    def test_second_load_is_rejected_without_duplicates(self, db_manager, loaded_pack):
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = loaded_pack
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent):
            with pytest.raises(psycopg2.errors.UniqueViolation):
                load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT COUNT(*) FROM households WHERE household_id IN ('hh_8_1_100', 'hh_8_1_200')",
            fetch=True,
        )
        assert rows[0][0] == 2
        rows = db_manager.execute(
            "SELECT COUNT(*) FROM communities WHERE community_id = %s",
            (PACK_COMMUNITY_ID,),
            fetch=True,
        )
        assert rows[0][0] == 1


class TestLoadPackNotFound:
    """Test error handling for missing packs (no database needed)."""

    def test_missing_pack_exits_with_error(self, tmp_path, capsys):
        from backend.src.research.load_pack import load_pack

        with patch("backend.src.research.load_pack.OUTPUT_DIR", tmp_path):
            with pytest.raises(SystemExit) as exc:
                load_pack("nonexistent_1")
        assert exc.value.code == 1
        assert "Pack not found" in capsys.readouterr().out
