# db/schema.py
class SchemaManager:

    def __init__(self, db_manager):
        self.db = db_manager

    def _drop_all_tables_in_public(self):
        query = """
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
        self.db.execute(query)

    def _drop_forecasting_tables_in_public(self):
        forecast_tables = [
            f"{source}_forecast" for source in self.db.renewables + ["load", "market"]
        ]
        query = """
        DO $$
        DECLARE
            tbl record;
        BEGIN
            FOR tbl IN
                SELECT tablename 
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = ANY(%s)
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
            END LOOP;
        END $$;
        """
        self.db.execute(query, (forecast_tables,))

    def _create_energy_sources_table(self):
        query = """
        CREATE TABLE energy_sources (
            source_id VARCHAR(50) PRIMARY KEY,
            type VARCHAR(50) NOT NULL CHECK (type IN ('solar', 'wind')),
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            name VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _create_batteries_table(self):
        query = """
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
        self.db.execute(query)

    def _create_market_table(self):
        market_query = """
        CREATE TABLE market (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('market', 'time');
        """
        self.db.execute(market_query)

    def _create_market_forecast_table(self):
        query = """
            CREATE TABLE market_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION
        );
        SELECT create_hypertable('market_forecast', 'time');
        """
        self.db.execute(query)

    def _create_load_table(self):
        load_query = """
        CREATE TABLE load (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('load', 'time');
        """
        self.db.execute(load_query)

    def _create_load_forecast_table(self):
        query = """
            CREATE TABLE load_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION
        );
        SELECT create_hypertable('load_forecast', 'time');
        """
        self.db.execute(query)

    def _create_renewables_tables(self):
        for renewable in self.db.renewables:
            query = f"""
            CREATE TABLE {renewable} (
                time        TIMESTAMPTZ NOT NULL,
                source_id   VARCHAR(50),
                value       DOUBLE PRECISION
            );
            SELECT create_hypertable('{renewable}', 'time');
            """.strip()
            self.db.execute(query)

    def _create_renewables_forecast_tables(self):
        for renewable in self.db.renewables:
            query = f"""
            CREATE TABLE {renewable}_forecast (
                time    TIMESTAMPTZ NOT NULL,
                source_id VARCHAR(50),
                yhat    DOUBLE PRECISION
            );
            SELECT create_hypertable('{renewable}_forecast', 'time');
            """
            self.db.execute(query)

    def reset_all_tables(self):
        self._drop_all_tables_in_public()

        self._create_energy_sources_table()
        self._create_batteries_table()
        self._create_market_table()
        self._create_market_forecast_table()
        self._create_load_table()
        self._create_load_forecast_table()
        self._create_renewables_tables()
        self._create_renewables_forecast_tables()

    def reset_forecast_tables(self):
        self._drop_forecasting_tables_in_public()

        self._create_market_forecast_table()
        self._create_load_forecast_table()
        self._create_renewables_forecast_tables()
