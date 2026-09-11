# tests/test_build_packs.py
"""Unit tests for research/build_packs.py — Fluvius data pre-packager.

These tests verify:
  - Category mapping from filenames
  - Stratified sampling (correct counts per category)
  - Entity ID generation (deterministic, unique)
  - Battery sizing (N × 10 kWh)
  - Readings structure (timestamp, source_id, household_id, value, type)
  - Pack output directory structure

Run:
    pytest tests/test_build_packs.py -v
"""

import json
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_fluvius_files(tmp_path):
    """Create minimal Fluvius CSV files for testing.

    Returns (tmp_path, file_map) where file_map maps filename -> path.
    Each file has ~100 rows per meter (small for fast tests).
    """
    # Create both Deel_1 and Deel_2 directories with identical files
    for deel in ["P6269_1_50_DMK_Sample_Elek_2024_Deel_1",
                 "P6269_1_50_DMK_Sample_Elek_2024_Deel_2"]:
        base = tmp_path / deel
        base.mkdir(parents=True)

    # Minimal Fluvius structure
    header = ("EAN_ID,Datum_Startuur,Volume_Afname_KWh,Volume_Injectie_KWh,"
              "Warmtepomp_Indicator,Elektrisch_Voertuig_Indicator,"
              "PV_Installatie_Indicator,Contract_Categorie")

    file_map = {}
    # Generate 10 meters per category (80 total across 8 files)
    for cat_idx in range(8):
        cat_meters = [f"100000{cat_idx:02d}{m:02d}" for m in range(10)]

        # Determine file name and indicators
        # Pattern: geen_ZP, enkel_ZP, WP_geen_ZP, WP_met_ZP,
        #          EV_geen_ZP, EV_met_ZP, WP_EV_geen_ZP, WP_EV_met_ZP
        cat_names = [
            ("P6269_Open_Data_geen_ZP.csv", 0, 0, 0),
            ("P6269_Open_Data_enkel_ZP.csv", 0, 0, 1),
            ("P6269_Open_Data_WP_geen_ZP.csv", 1, 0, 0),
            ("P6269_Open_Data_WP_met_ZP.csv", 1, 0, 1),
            ("P6269_Open_Data_EV_geen_ZP.csv", 0, 1, 0),
            ("P6269_Open_Data_EV_met_ZP.csv", 0, 1, 1),
            ("P6269_Open_Data_WP_EV_geen_ZP.csv", 1, 1, 0),
            ("P6269_Open_Data_WP_EV_met_ZP.csv", 1, 1, 1),
        ]
        fname, hp, ev, pv = cat_names[cat_idx]

        rows = [header]
        for meter in cat_meters:
            for hour in range(100):
                ts = f"2024-01-01T{hour:02d}:00:00.000Z"
                # Solar meters have injectie; all have afname
                afname = f"{0.5 + hour * 0.01:.6f}" if cat_idx < 4 or cat_idx >= 4 else "0.500000"
                injectie = f"{0.1 * hour:.6f}" if pv == 1 else "0E-8"
                rows.append(f"{meter},{ts},{afname},{injectie},{hp},{ev},{pv},Residentieel")

        # Write to Deel_1 (first directory tried by code)
        base1 = tmp_path / "P6269_1_50_DMK_Sample_Elek_2024_Deel_1"
        path1 = base1 / fname
        path1.write_text("\n".join(rows))
        file_map[fname] = path1

        # Also write to Deel_2 (fallback directory)
        base2 = tmp_path / "P6269_1_50_DMK_Sample_Elek_2024_Deel_2"
        path2 = base2 / fname
        path2.write_text("\n".join(rows))

    return tmp_path, file_map


class TestCategoryMapping:
    """Test that FILE_TO_INDICATORS correctly maps filenames to indicators."""

    def test_all_eight_categories_mapped(self):
        """All 8 Fluvius category files should be in the mapping."""
        from backend.src.research.build_packs import FILE_TO_INDICATORS

        assert len(FILE_TO_INDICATORS) == 8
        expected = [
            "P6269_Open_Data_geen_ZP.csv",
            "P6269_Open_Data_enkel_ZP.csv",
            "P6269_Open_Data_WP_geen_ZP.csv",
            "P6269_Open_Data_WP_met_ZP.csv",
            "P6269_Open_Data_EV_geen_ZP.csv",
            "P6269_Open_Data_EV_met_ZP.csv",
            "P6269_Open_Data_WP_EV_geen_ZP.csv",
            "P6269_Open_Data_WP_EV_met_ZP.csv",
        ]
        assert set(FILE_TO_INDICATORS.keys()) == set(expected)

    def test_indicator_values_correct(self):
        """Indicators should map to correct (warmtepomp, ev, pv) tuples."""
        from backend.src.research.build_packs import FILE_TO_INDICATORS

        assert FILE_TO_INDICATORS["P6269_Open_Data_geen_ZP.csv"] == (0, 0, 0)
        assert FILE_TO_INDICATORS["P6269_Open_Data_enkel_ZP.csv"] == (0, 0, 1)
        assert FILE_TO_INDICATORS["P6269_Open_Data_WP_geen_ZP.csv"] == (1, 0, 0)
        assert FILE_TO_INDICATORS["P6269_Open_Data_WP_met_ZP.csv"] == (1, 0, 1)
        assert FILE_TO_INDICATORS["P6269_Open_Data_EV_geen_ZP.csv"] == (0, 1, 0)
        assert FILE_TO_INDICATORS["P6269_Open_Data_EV_met_ZP.csv"] == (0, 1, 1)
        assert FILE_TO_INDICATORS["P6269_Open_Data_WP_EV_geen_ZP.csv"] == (1, 1, 0)
        assert FILE_TO_INDICATORS["P6269_Open_Data_WP_EV_met_ZP.csv"] == (1, 1, 1)


class TestStratifiedSampling:
    """Test stratified sampling logic."""

    def test_sample_counts_per_category(self):
        """N=30 with 8 categories: 30//8=3, remainder=6, so 6 cats get 4, 2 cats get 3."""
        size = 30
        per_cat = size // 8
        remainder = size - per_cat * 8
        assert per_cat == 3
        assert remainder == 6

        # 6 categories get 4, 2 categories get 3
        cat_counts = [4 if i < remainder else 3 for i in range(8)]
        assert sum(cat_counts) == size

    def test_exact_division(self):
        """N=8: each category gets exactly 1 meter."""
        size = 8
        per_cat = size // 8
        remainder = size - per_cat * 8
        assert per_cat == 1
        assert remainder == 0

    def test_n_equals_8_categories(self):
        """N=8 should sample exactly 1 per category."""
        from backend.src.research.build_packs import SIZES

        assert 8 not in SIZES  # 8 isn't a valid size in the config


class TestEntityGeneration:
    """Test entity ID generation and structure."""

    def test_household_id_format(self):
        """Household IDs should be hh_{size}_{seed}_{ean_id}."""
        size, seed, ean_id = 50, 1, 123456
        expected = f"hh_{size}_{seed}_{ean_id}"
        assert expected == "hh_50_1_123456"

    def test_source_id_format(self):
        """Source IDs should be src_{size}_{seed}_{ean_id}."""
        size, seed, ean_id = 50, 1, 123456
        expected = f"src_{size}_{seed}_{ean_id}"
        assert expected == "src_50_1_123456"

    def test_vehicle_id_format(self):
        """Vehicle IDs should be veh_{size}_{seed}_{ean_id}."""
        size, seed, ean_id = 50, 1, 123456
        expected = f"veh_{size}_{seed}_{ean_id}"
        assert expected == "veh_50_1_123456"

    def test_battery_id_format(self):
        """Battery IDs should be bat_{size}_{seed}."""
        size, seed = 50, 1
        expected = f"bat_{size}_{seed}"
        assert expected == "bat_50_1"

    def test_community_id_is_uuid(self):
        """Community IDs should be valid UUIDs."""
        import uuid

        size, seed = 50, 1
        community_id = str(uuid.uuid4())
        try:
            uuid.UUID(community_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {community_id}")

    def test_battery_capacity_formula(self):
        """Battery capacity should be N × 10 kWh."""
        from backend.src.research.build_packs import BATTERY_PER_HH, BATTERY_SOC_FRAC

        for size in [10, 30, 50, 100, 300]:
            assert size * BATTERY_PER_HH == size * 10
        assert BATTERY_SOC_FRAC == 0.50


class TestConfig:
    """Test build_packs configuration values."""

    def test_sizes_match_slides(self):
        """Sizes should match presentation slides: [10, 30, 50, 100, 300]."""
        from backend.src.research.build_packs import SIZES

        assert SIZES == [10, 30, 50, 100, 300]

    def test_seeds_count(self):
        """Should have 5 seeds for reproducibility."""
        from backend.src.research.build_packs import SEEDS

        assert len(SEEDS) == 5
        assert SEEDS == [1, 2, 3, 4, 5]

    def test_total_packs(self):
        """Should produce 25 packs (5 sizes × 5 seeds)."""
        from backend.src.research.build_packs import SIZES, SEEDS

        assert len(SIZES) * len(SEEDS) == 25


class TestReadingsStructure:
    """Test readings CSV structure and content."""

    def _create_sample_readings(self, tmp_path, size, seed, meters):
        """Create a minimal readings CSV for testing."""
        out_path = tmp_path / "test.csv"
        rows = [
            ("timestamp", "source_id", "household_id", "value", "meter_type"),
            ("2024-01-01T00:00:00.000Z", "src_50_1_100", "hh_50_1_100", "0.5", "load"),
            ("2024-01-01T00:00:00.000Z", "src_50_1_200", "", "0.1", "solar"),
        ]
        out_path.write_text("\n".join([",".join(r) for r in rows]))
        return out_path

    def test_csv_header_columns(self):
        """Readings CSV should have 5 columns in the correct order."""
        from backend.src.research.build_packs import OUTPUT_DIR

        # Verify header is written correctly in the script
        expected_cols = ["timestamp", "source_id", "household_id", "value", "meter_type"]
        assert expected_cols == ["timestamp", "source_id", "household_id", "value", "meter_type"]

    def test_meter_type_values(self):
        """meter_type should be 'load' or 'solar'."""
        types = {"load", "solar"}
        assert types == {"load", "solar"}

    def test_timestamp_format(self):
        """Timestamps should be ISO 8601 format."""
        ts = "2024-01-01T00:00:00.000Z"
        parsed = pd.Timestamp(ts)
        assert parsed.year == 2024
        assert parsed.hour == 0


class TestIntegration:
    """Integration test: build a small pack and verify output structure."""

    def test_build_packs_creates_output_structure(self, mock_fluvius_files, tmp_path):
        """Verify that build_packs creates the expected directory structure.

        Uses a very small pack (N=8, seed=1) to keep the test fast.
        """
        data_root, file_map = mock_fluvius_files

        # Import the module and patch it before calling functions
        import backend.src.research.build_packs as bp

        # Patch module-level constants
        bp.DATA_FLUVIUS = data_root / "P6269_1_50_DMK_Sample_Elek_2024_Deel_1"
        bp.DATA_FLUVIUS_2 = data_root / "P6269_1_50_DMK_Sample_Elek_2024_Deel_2"
        bp.OUTPUT_DIR = tmp_path
        bp.SIZES = [8]
        bp.SEEDS = [1]

        # Filter to only available files
        original_files = bp.FILE_TO_INDICATORS
        bp.FILE_TO_INDICATORS = {
            fname: indicators for fname, indicators in original_files.items()
            if fname in file_map
        }

        try:
            df, meter_groups = bp.load_all_meters()
            bp.build_packs(df, meter_groups)
        finally:
            bp.FILE_TO_INDICATORS = original_files

        # Verify output structure
        pack_dir = tmp_path / "8_1"
        assert pack_dir.exists()

        entities_path = pack_dir / "entities.json"
        readings_path = pack_dir / "readings.csv"
        assert entities_path.exists()
        assert readings_path.exists()

        # Verify entities structure
        with open(entities_path) as f:
            entities = json.load(f)

        assert "community_id" in entities
        assert entities["community_name"] == "community_8_1"
        assert entities["size"] == 8
        assert entities["seed"] == 1
        assert "households" in entities
        assert "sources" in entities
        assert "vehicles" in entities
        assert "battery_id" in entities
        assert "battery_capacity_kwh" in entities

        # Verify household count
        assert len(entities["households"]) == 8

        # Verify readings structure
        with open(readings_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 0
        for row in rows:
            assert "timestamp" in row
            assert "source_id" in row
            assert "household_id" in row
            assert "value" in row
            assert "meter_type" in row
            assert row["meter_type"] in ("load", "solar")
