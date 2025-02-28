# tests/test_schema.py
import pytest
from unittest.mock import Mock
from backend.src.db.schema import SchemaManager
from backend.src.db.connection import DatabaseManager


@pytest.fixture
def mock_db_manager(mocker):
    """Fixture to create a mocked DatabaseManager."""
    db = Mock(spec=DatabaseManager)
    db.renewables = ["solar", "wind"]  # Match the expected renewables
    db.execute = Mock()  # Mock the execute method
    return db


@pytest.fixture
def schema_manager(mock_db_manager):
    """Fixture to create a SchemaManager instance with a mocked db."""
    return SchemaManager(mock_db_manager)


def test_init(schema_manager, mock_db_manager):
    """Test SchemaManager initialization."""
    assert schema_manager.db == mock_db_manager
    assert schema_manager.db.renewables == ["solar", "wind"]


def test_drop_all_tables_in_public(schema_manager, mocker):
    """Test dropping all tables in the public schema."""
    expected_query = """
        DO $$
        DECLARE
            tbl record;
        BEGIN
            FOR tbl IN
                SELECT tablename 
                FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
            END LOOP;
        END $$;
        """
    schema_manager._drop_all_tables_in_public()
    schema_manager.db.execute.assert_called_once_with(expected_query)


# def test_drop_forecasting_tables_in_public(schema_manager, mocker):
#     """Test dropping only forecasting tables."""
#     expected_forecast_tables = [
#         "solar_forecast",
#         "wind_forecast",
#         "load_forecast",
#         "market_forecast",
#     ]
#     expected_query = """
#         DO $$
#         DECLARE
#             tbl record;
#         BEGIN
#             FOR tbl IN
#                 SELECT tablename
#                 FROM pg_tables
#                 WHERE schemaname = 'public'
#                 AND tablename = ANY(%s)
#             LOOP
#                 EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
#             END LOOP;
#         END $$;
#         """
#     schema_manager._drop_forecasting_tables_in_public()
#     schema_manager.db.execute.assert_called_once_with(
#         expected_query, (expected_forecast_tables,)
#     )


def test_create_energy_sources_table(schema_manager):
    """Test creation of energy_sources table."""
    expected_query = """
        CREATE TABLE energy_sources (
            source_id VARCHAR(50) PRIMARY KEY,
            type VARCHAR(50) NOT NULL CHECK (type IN ('solar', 'wind')),
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            name VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
    schema_manager._create_energy_sources_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_batteries_table(schema_manager):
    """Test creation of batteries hypertable."""
    expected_query = """
        CREATE TABLE batteries (
            time TIMESTAMPTZ NOT NULL,
            battery_id VARCHAR(50),
            capacity_kWh DOUBLE PRECISION,
            soc_kWh DOUBLE PRECISION,
            max_charge_kW DOUBLE PRECISION,
            max_discharge_kW DOUBLE PRECISION,
            eta DOUBLE PRECISION
        );
        SELECT create_hypertable('batteries', 'time');
        """
    schema_manager._create_batteries_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_market_table(schema_manager):
    """Test creation of market hypertable."""
    expected_query = """
        CREATE TABLE market (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('market', 'time');
        """
    schema_manager._create_market_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_market_forecast_table(schema_manager):
    """Test creation of market_forecast hypertable."""
    expected_query = """
            CREATE TABLE market_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION
        );
        SELECT create_hypertable('market_forecast', 'time');
        """
    schema_manager._create_market_forecast_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_load_table(schema_manager):
    """Test creation of load hypertable."""
    expected_query = """
        CREATE TABLE load (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('load', 'time');
        """
    schema_manager._create_load_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_load_forecast_table(schema_manager):
    """Test creation of load_forecast hypertable."""
    expected_query = """
            CREATE TABLE load_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION
        );
        SELECT create_hypertable('load_forecast', 'time');
        """
    schema_manager._create_load_forecast_table()
    schema_manager.db.execute.assert_called_once_with(expected_query)


def test_create_renewables_tables(schema_manager):
    """Test creation of renewables tables (solar, wind)."""
    expected_queries = [
        f"""CREATE TABLE {renewable} (
            time        TIMESTAMPTZ NOT NULL,
            source_id   VARCHAR(50),
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('{renewable}', 'time');
        """
        for renewable in ["solar", "wind"]
    ]
    schema_manager._create_renewables_tables()
    assert schema_manager.db.execute.call_count == 2
    calls = [call[0][0] for call in schema_manager.db.execute.call_args_list]
    calls_clean = [
        "".join(call.split()) for call in calls
    ]  # Remove whitespace to compare strings
    expected_clean = ["".join(query.split()) for query in expected_queries]
    assert calls_clean == expected_clean  # Compare queries after removing whitespace


def test_create_renewables_forecast_tables(schema_manager):
    """Test creation of renewables forecast tables (solar_forecast, wind_forecast)."""
    expected_queries = [
        f"""
        CREATE TABLE {renewable}_forecast (
            time    TIMESTAMPTZ NOT NULL,
            source_id VARCHAR(50),
            yhat    DOUBLE PRECISION
        );
        SELECT create_hypertable('{renewable}_forecast', 'time');
        """
        for renewable in ["solar", "wind"]
    ]
    schema_manager._create_renewables_forecast_tables()
    assert schema_manager.db.execute.call_count == 2
    calls = [call[0][0] for call in schema_manager.db.execute.call_args_list]
    calls_clean = [
        "".join(call.split()) for call in calls
    ]  # Remove whitespace to compare strings
    expected_clean = ["".join(query.split()) for query in expected_queries]
    assert calls_clean == expected_clean  # Compare queries after removing whitespace


def test_reset_all_tables(schema_manager, mocker):
    """Test reset_all_tables calls all create methods."""
    mocker.patch.object(schema_manager, "_drop_all_tables_in_public")
    mocker.patch.object(schema_manager, "_create_energy_sources_table")
    mocker.patch.object(schema_manager, "_create_batteries_table")
    mocker.patch.object(schema_manager, "_create_market_table")
    mocker.patch.object(schema_manager, "_create_market_forecast_table")
    mocker.patch.object(schema_manager, "_create_load_table")
    mocker.patch.object(schema_manager, "_create_load_forecast_table")
    mocker.patch.object(schema_manager, "_create_renewables_tables")
    mocker.patch.object(schema_manager, "_create_renewables_forecast_tables")

    schema_manager.reset_all_tables()

    schema_manager._drop_all_tables_in_public.assert_called_once()
    schema_manager._create_energy_sources_table.assert_called_once()
    schema_manager._create_batteries_table.assert_called_once()
    schema_manager._create_market_table.assert_called_once()
    schema_manager._create_market_forecast_table.assert_called_once()
    schema_manager._create_load_table.assert_called_once()
    schema_manager._create_load_forecast_table.assert_called_once()
    schema_manager._create_renewables_tables.assert_called_once()
    schema_manager._create_renewables_forecast_tables.assert_called_once()


def test_reset_forecast_tables(schema_manager, mocker):
    """Test reset_forecast_tables calls forecast-related create methods."""
    mocker.patch.object(schema_manager, "_drop_forecasting_tables_in_public")
    mocker.patch.object(schema_manager, "_create_market_forecast_table")
    mocker.patch.object(schema_manager, "_create_load_forecast_table")
    mocker.patch.object(schema_manager, "_create_renewables_forecast_tables")

    schema_manager.reset_forecast_tables()

    schema_manager._drop_forecasting_tables_in_public.assert_called_once()
    schema_manager._create_market_forecast_table.assert_called_once()
    schema_manager._create_load_forecast_table.assert_called_once()
    schema_manager._create_renewables_forecast_tables.assert_called_once()
