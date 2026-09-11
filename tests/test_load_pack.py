# tests/test_load_pack.py
"""Integration tests for research/load_pack.py — community pack bootstrap.

These tests verify:
  - Admin user creation (idempotent)
  - Community, household, source, vehicle, battery loading
  - Readings bulk-insertion
  - Pack idempotency (loading twice doesn't duplicate)

Run:
    pytest tests/test_load_pack.py -v -k integration
"""

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import bcrypt


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
                "max_discharge_kw": 0.0,
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


@pytest.mark.integration
class TestLoadPackAdminUser:
    """Test admin user creation logic."""

    def test_admin_user_created(self, db_manager):
        """First load should create the admin user."""
        from backend.src.research.load_pack import ensure_admin_user

        # Check if admin user already exists (from previous test runs)
        existing = db_manager.execute(
            "SELECT 1 FROM users WHERE user_id = %s LIMIT 1",
            ("admin",),
            fetch=True,
        )
        if not existing:
            ensure_admin_user(db_manager)

        rows = db_manager.execute(
            "SELECT user_id, username FROM users WHERE user_id = %s",
            ("admin",),
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["user_id"] == "admin"
        assert rows[0]["username"] == "admin"

    def test_admin_user_idempotent(self, db_manager):
        """Calling ensure_admin_user twice should not create duplicates."""
        from backend.src.research.load_pack import ensure_admin_user

        ensure_admin_user(db_manager)
        ensure_admin_user(db_manager)

        rows = db_manager.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE user_id = %s",
            ("admin",),
            fetch=True,
        )
        assert rows[0]["cnt"] == 1

    def test_admin_password_hashed(self, db_manager):
        """Admin password should be bcrypt-hashed."""
        from backend.src.research.load_pack import ensure_admin_user

        ensure_admin_user(db_manager)

        rows = db_manager.execute(
            "SELECT hashed_password FROM users WHERE user_id = %s",
            ("admin",),
            fetch=True,
        )
        hashed = rows[0]["hashed_password"]
        # Should be a bcrypt hash (starts with $2b$)
        assert hashed.startswith("$2b$")
        # Verify the password works
        assert bcrypt.checkpw(
            b"admin",
            hashed.encode(),
        )


@pytest.mark.integration
class TestLoadPackEntities:
    """Test loading entity metadata."""

    def test_community_loaded(self, db_manager, sample_pack_dir):
        """Community should be created in the database."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT community_id, name FROM communities WHERE community_id = %s",
            ("c1234567-89ab-cdef-0123-456789abcdef",),
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "test_community"

    def test_households_loaded(self, db_manager, sample_pack_dir):
        """Households should be created with correct IDs."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT household_id, name, solar_panels, num_evs "
            "FROM households WHERE household_id IN ('hh_8_1_100', 'hh_8_1_200')",
            fetch=True,
        )
        assert len(rows) == 2

        # Find each household
        hh100 = next(r for r in rows if r["household_id"] == "hh_8_1_100")
        hh200 = next(r for r in rows if r["household_id"] == "hh_8_1_200")

        assert hh100["solar_panels"] == 1
        assert hh200["solar_panels"] == 0
        assert hh200["num_evs"] == 1

    def test_sources_loaded(self, db_manager, sample_pack_dir):
        """Solar sources should be created with correct household FK."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT source_id, type, household_id FROM energy_sources "
            "WHERE source_id = 'src_8_1_100'",
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["type"] == "solar"
        assert rows[0]["household_id"] == "hh_8_1_100"

    def test_vehicles_loaded(self, db_manager, sample_pack_dir):
        """EV vehicles should be created with correct household FK."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT vehicle_id, household_id, capacity_kwh, soc_kwh "
            "FROM electric_vehicles WHERE vehicle_id = 'veh_8_1_200'",
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["household_id"] == "hh_8_1_200"
        assert rows[0]["capacity_kwh"] == 60.0
        assert rows[0]["soc_kwh"] == 30.0

    def test_battery_loaded(self, db_manager, sample_pack_dir):
        """Community battery should be created with correct capacity."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT battery_id, capacity_kwh, soc_kwh FROM batteries "
            "WHERE battery_id = 'bat_8_1'",
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["capacity_kwh"] == 80.0  # 8 × 10
        assert rows[0]["soc_kwh"] == 40.0  # 80.0 × 0.5


@pytest.mark.integration
class TestLoadPackReadings:
    """Test bulk-insertion of readings."""

    def test_readings_loaded(self, db_manager, sample_pack_dir):
        """Readings should be inserted into solar and household_load tables."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        # Check solar readings
        solar_rows = db_manager.execute(
            "SELECT COUNT(*) as cnt FROM solar",
            fetch=True,
        )
        assert solar_rows[0]["cnt"] == 2  # 2 solar rows in test data

        # Check load readings
        load_rows = db_manager.execute(
            "SELECT COUNT(*) as cnt FROM household_load",
            fetch=True,
        )
        assert load_rows[0]["cnt"] == 2  # 2 load rows in test data

    def test_readings_timestamps_correct(self, db_manager, sample_pack_dir):
        """Timestamps should be correctly parsed and stored."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)

        rows = db_manager.execute(
            "SELECT time FROM solar ORDER BY time ASC",
            fetch=True,
        )
        assert len(rows) == 2
        # Timestamps should be valid
        assert rows[0]["time"] is not None


@pytest.mark.integration
class TestLoadPackIdempotency:
    """Test that loading the same pack twice doesn't create duplicates."""

    def test_load_pack_twice_no_duplicates(self, db_manager, sample_pack_dir):
        """Loading a pack twice should not duplicate entities."""
        from backend.src.research.load_pack import load_pack

        pack_dir, pack_name = sample_pack_dir
        with patch("backend.src.research.load_pack.OUTPUT_DIR", pack_dir.parent.parent):
            load_pack(pack_name)
            load_pack(pack_name)  # Load again

        # Check household count
        rows = db_manager.execute(
            "SELECT COUNT(*) as cnt FROM households "
            "WHERE household_id IN ('hh_8_1_100', 'hh_8_1_200')",
            fetch=True,
        )
        assert rows[0]["cnt"] == 2  # Should still be 2, not 4

        # Check community count
        rows = db_manager.execute(
            "SELECT COUNT(*) as cnt FROM communities "
            "WHERE community_id = 'c1234567-89ab-cdef-0123-456789abcdef'",
            fetch=True,
        )
        assert rows[0]["cnt"] == 1  # Should still be 1, not 2


@pytest.mark.integration
class TestLoadPackNotFound:
    """Test error handling for missing packs."""

    def test_missing_pack_raises_error(self, tmp_path):
        """Loading a non-existent pack should exit with error."""
        import sys
        from io import StringIO
        from backend.src.research.load_pack import load_pack

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            load_pack("nonexistent_1")
        except SystemExit as e:
            assert e.code == 1
        finally:
            sys.stderr = old_stderr
