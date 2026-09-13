# tests/test_db_schema.py
"""Unit tests for SchemaManager orchestration.

These tests check *what* runs and in which order, not the SQL text of each
statement. Table shapes are verified against a real database in
tests/test_db_integration.py.
"""
from unittest.mock import Mock

import pytest

from backend.src.db.connection import DatabaseManager
from backend.src.db.schema import SchemaManager


@pytest.fixture
def mock_db_manager():
    db = Mock(spec=DatabaseManager)
    db.renewables = ["solar"]
    return db


@pytest.fixture
def schema_manager(mock_db_manager):
    return SchemaManager(mock_db_manager)


@pytest.fixture
def recorded(schema_manager, monkeypatch):
    """Replace every private schema step with a recorder and return the call log."""
    calls = []
    for name in dir(SchemaManager):
        if name.startswith(("_create_", "_migrate_", "_drop_")):
            monkeypatch.setattr(schema_manager, name, lambda _n=name: calls.append(_n))
    monkeypatch.setattr(schema_manager, "_try_create", lambda fn: fn())
    return calls


def _before(calls, first, second):
    return calls.index(first) < calls.index(second)


def test_init(schema_manager, mock_db_manager):
    assert schema_manager.db is mock_db_manager


def test_reset_all_tables_drops_first(schema_manager, recorded):
    schema_manager.reset_all_tables()
    assert recorded[0] == "_drop_all_tables"
    assert recorded.count("_drop_all_tables") == 1


def test_reset_all_tables_respects_foreign_keys(schema_manager, recorded):
    schema_manager.reset_all_tables()
    assert _before(recorded, "_create_communities_table", "_create_households_table")
    for dependent in (
        "_create_energy_sources_table",
        "_create_electric_vehicles_table",
        "_create_household_load_table",
        "_create_batteries_table",
    ):
        assert _before(recorded, "_create_households_table", dependent)
    assert _before(recorded, "_create_batteries_table", "_migrate_add_community_id")


def test_reset_all_tables_creates_every_table(schema_manager, recorded):
    schema_manager.reset_all_tables()
    creates = {name for name in dir(SchemaManager) if name.startswith("_create_")}
    assert creates <= set(recorded)


def test_init_all_tables_never_drops(schema_manager, recorded):
    schema_manager.init_all_tables()
    assert not [c for c in recorded if c.startswith("_drop_")]
    assert "_migrate_relax_legacy_user_scoping" in recorded


def test_reset_forecast_tables(schema_manager, recorded):
    schema_manager.reset_forecast_tables()
    assert recorded == [
        "_drop_forecasting_tables_in_public",
        "_create_market_forecast_table",
        "_create_load_forecast_table",
        "_create_renewables_forecast_tables",
    ]


def test_drop_forecasting_tables_targets_only_known_tables(schema_manager, mock_db_manager):
    schema_manager._drop_forecasting_tables_in_public()
    (query,), _ = mock_db_manager.execute.call_args
    assert query == "DROP TABLE IF EXISTS solar_forecast, wind_forecast, load_forecast, market_forecast CASCADE;"
    assert "LIKE" not in query.upper()
