# db/schema.py
from .connection import DatabaseManager


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
        query = """
        DO $$
        DECLARE
            tbl record;
        BEGIN
            FOR tbl IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename ILIKE '%forecast%'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
            END LOOP;
        END $$;
        """
        self.db.execute(query)

    def _create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id     VARCHAR(50) PRIMARY KEY,
            username    VARCHAR(100) UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _migrate_add_user_id(self):
        """Additive migration: add user_id FK to households and energy_sources if missing."""
        for table in ("households", "energy_sources"):
            self.db.execute(f"""
                ALTER TABLE {table}
                ADD COLUMN IF NOT EXISTS user_id VARCHAR(50)
                REFERENCES users(user_id) ON DELETE CASCADE;
            """)

    def _migrate_add_building_geometry(self):
        """Additive migration: add geometry column to households if missing."""
        self.db.execute("""
            ALTER TABLE households
            ADD COLUMN IF NOT EXISTS geometry JSONB;
        """)

    def _create_households_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS households (
            household_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            solar_panels INT DEFAULT 0,
            building_type VARCHAR(20) DEFAULT 'household',
            num_people INT DEFAULT 1,
            num_evs INT DEFAULT 0,
            osm_feature_id VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _create_energy_sources_table(self):
        # Must be created AFTER households (FK reference)
        query = """
        CREATE TABLE energy_sources (
            source_id VARCHAR(50) PRIMARY KEY,
            type VARCHAR(50) NOT NULL CHECK (type IN ('solar', 'wind')),
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            name VARCHAR(100),
            household_id VARCHAR(50) REFERENCES households(household_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _create_market_table(self):
        market_query = """
        CREATE TABLE market (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION NOT NULL
        );
        SELECT create_hypertable('market', 'time');
        CREATE INDEX idx_market_time ON market(time DESC);
        """
        self.db.execute(market_query)

    def _create_market_forecast_table(self):
        query = """
            CREATE TABLE market_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION NOT NULL
        );
        SELECT create_hypertable('market_forecast', 'time');
        CREATE INDEX idx_market_forecast_time ON market_forecast(time DESC);
        """
        self.db.execute(query)

    def _create_load_table(self):
        load_query = """
        CREATE TABLE load (
            time        TIMESTAMPTZ NOT NULL,
            value       DOUBLE PRECISION NOT NULL
        );
        SELECT create_hypertable('load', 'time');
        CREATE INDEX idx_load_time ON load(time DESC);
        """
        self.db.execute(load_query)

    def _create_load_forecast_table(self):
        query = """
            CREATE TABLE load_forecast (
            time    TIMESTAMPTZ NOT NULL,
            yhat    DOUBLE PRECISION NOT NULL
        );
        SELECT create_hypertable('load_forecast', 'time');
        CREATE INDEX idx_load_forecast_time ON load_forecast(time DESC);
        """
        self.db.execute(query)

    def _create_renewables_tables(self):
        for renewable in self.db.renewables:
            self._try_create(lambda r=renewable: self.db.execute(f"""
            CREATE TABLE {r} (
                time        TIMESTAMPTZ NOT NULL,
                source_id   VARCHAR(50) NOT NULL,
                value       DOUBLE PRECISION NOT NULL CHECK (value >= 0)
            );
            SELECT create_hypertable('{r}', 'time');
            CREATE INDEX idx_{r}_source_time ON {r}(source_id, time DESC);
            """.strip()))

    def _create_renewables_forecast_tables(self):
        for renewable in self.db.renewables:
            self._try_create(lambda r=renewable: self.db.execute(f"""
            CREATE TABLE {r}_forecast (
                time    TIMESTAMPTZ NOT NULL,
                source_id VARCHAR(50) NOT NULL,
                yhat    DOUBLE PRECISION NOT NULL CHECK (yhat >= 0)
            );
            SELECT create_hypertable('{r}_forecast', 'time');
            CREATE INDEX idx_{r}_forecast_source_time ON {r}_forecast(source_id, time DESC);
            """))

    def _create_electric_vehicles_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS electric_vehicles (
            vehicle_id VARCHAR(50) PRIMARY KEY,
            household_id VARCHAR(50) REFERENCES households(household_id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            capacity_kwh DOUBLE PRECISION NOT NULL CHECK (capacity_kwh > 0),
            soc_kwh DOUBLE PRECISION NOT NULL CHECK (soc_kwh >= 0),
            max_charge_kw DOUBLE PRECISION NOT NULL CHECK (max_charge_kw > 0),
            max_discharge_kw DOUBLE PRECISION NOT NULL CHECK (max_discharge_kw > 0),
            eta DOUBLE PRECISION NOT NULL CHECK (eta > 0 AND eta <= 1),
            status VARCHAR(20) DEFAULT 'home' CHECK (status IN ('home', 'away')),
            latitude FLOAT,
            longitude FLOAT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _create_tariffs_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS tariffs (
            tariff_id   VARCHAR(50) PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            tariff_type VARCHAR(20) NOT NULL CHECK (tariff_type IN ('grid_import', 'grid_export')),
            currency    VARCHAR(3) DEFAULT 'EUR',
            active      BOOLEAN DEFAULT false,
            created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tariff_periods (
            id           SERIAL PRIMARY KEY,
            tariff_id    VARCHAR(50) NOT NULL REFERENCES tariffs(tariff_id) ON DELETE CASCADE,
            day_type     VARCHAR(10) NOT NULL CHECK (day_type IN ('weekday', 'weekend', 'all')),
            hour_start   INT NOT NULL CHECK (hour_start >= 0 AND hour_start < 24),
            hour_end     INT NOT NULL CHECK (hour_end > 0 AND hour_end <= 24),
            price_per_kwh DOUBLE PRECISION NOT NULL,
            UNIQUE (tariff_id, day_type, hour_start)
        );

        CREATE TABLE IF NOT EXISTS community_settings (
            key   VARCHAR(50) PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
        self.db.execute(query)

    def _create_batteries_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS batteries (
            battery_id   VARCHAR(50) PRIMARY KEY,
            household_id VARCHAR(50) NOT NULL REFERENCES households(household_id) ON DELETE CASCADE,
            name         VARCHAR(100) NOT NULL,
            capacity_kwh DOUBLE PRECISION NOT NULL CHECK (capacity_kwh > 0),
            soc_kwh      DOUBLE PRECISION NOT NULL CHECK (soc_kwh >= 0),
            max_charge_kw    DOUBLE PRECISION NOT NULL CHECK (max_charge_kw > 0),
            max_discharge_kw DOUBLE PRECISION NOT NULL CHECK (max_discharge_kw > 0),
            eta          DOUBLE PRECISION NOT NULL CHECK (eta > 0 AND eta <= 1) DEFAULT 0.95,
            created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.db.execute(query)

    def _create_household_load_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS household_load (
            time TIMESTAMPTZ NOT NULL,
            household_id VARCHAR(50) NOT NULL REFERENCES households(household_id) ON DELETE CASCADE,
            value DOUBLE PRECISION NOT NULL
        );
        SELECT create_hypertable('household_load', 'time', if_not_exists => TRUE);
        CREATE INDEX IF NOT EXISTS idx_household_load_hid_time ON household_load(household_id, time DESC);
        """
        self.db.execute(query)

    def _migrate_household_load_fk(self):
        """Additive migration: add FK+cascade on household_load.household_id if missing."""
        self.db.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'household_load_household_id_fkey'
            ) THEN
                ALTER TABLE household_load
                ADD CONSTRAINT household_load_household_id_fkey
                FOREIGN KEY (household_id) REFERENCES households(household_id) ON DELETE CASCADE;
            END IF;
        END $$;
        """)

    def _migrate_energy_sources_allow_wind(self):
        """Update energy_sources type CHECK to allow 'wind' in addition to 'solar'."""
        self.db.execute("""
        DO $$
        BEGIN
            ALTER TABLE energy_sources DROP CONSTRAINT IF EXISTS energy_sources_type_check;
            ALTER TABLE energy_sources ADD CONSTRAINT energy_sources_type_check
                CHECK (type IN ('solar', 'wind'));
        EXCEPTION WHEN undefined_table THEN
            NULL;
        END $$;
        """)

    def _try_create(self, create_fn):
        """Run a create method, silently skip if the table already exists."""
        import psycopg2

        try:
            create_fn()
        except psycopg2.errors.DuplicateTable:
            pass

    def init_all_tables(self):
        """Create all tables only if they don't already exist. Safe to call on a live DB."""
        self._create_users_table()  # must come first — households FKs it
        # households first — energy_sources has a FK to it
        self._create_households_table()  # already uses IF NOT EXISTS
        self._try_create(self._create_energy_sources_table)
        self._try_create(self._create_market_table)
        self._try_create(self._create_market_forecast_table)
        self._try_create(self._create_load_table)
        self._try_create(self._create_load_forecast_table)
        self._create_renewables_tables()  # handles per-table try_create internally
        self._create_renewables_forecast_tables()  # handles per-table try_create internally
        self._create_electric_vehicles_table()  # already uses IF NOT EXISTS
        self._create_batteries_table()  # already uses IF NOT EXISTS
        self._create_tariffs_tables()  # already uses IF NOT EXISTS
        self._create_household_load_table()  # already uses IF NOT EXISTS
        self._migrate_add_user_id()  # idempotent: ADD COLUMN IF NOT EXISTS
        self._migrate_household_load_fk()  # idempotent: ADD CONSTRAINT IF NOT EXISTS
        self._migrate_add_building_geometry()  # idempotent: ADD COLUMN IF NOT EXISTS
        self._migrate_energy_sources_allow_wind()  # idempotent: update CHECK constraint

    def _drop_all_tables_except_users(self):
        """Drop all tables in public schema except the users table."""
        query = """
        DO $$
        DECLARE
            tbl record;
        BEGIN
            FOR tbl IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename != 'users'
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE;', tbl.tablename);
            END LOOP;
        END $$;
        """
        self.db.execute(query)

    def reset_all_tables(self):
        self._drop_all_tables_except_users()

        self._create_users_table()  # idempotent — preserved across reset
        # households must come before energy_sources (FK dependency)
        self._create_households_table()
        self._create_energy_sources_table()
        self._create_market_table()
        self._create_market_forecast_table()
        self._create_load_table()
        self._create_load_forecast_table()
        self._create_renewables_tables()
        self._create_renewables_forecast_tables()
        self._create_electric_vehicles_table()
        self._create_batteries_table()
        self._create_tariffs_tables()
        self._create_household_load_table()
        self._migrate_add_user_id()
        self._migrate_household_load_fk()
        self._migrate_add_building_geometry()
        self._migrate_energy_sources_allow_wind()

    def reset_forecast_tables(self):
        self._drop_forecasting_tables_in_public()

        self._create_market_forecast_table()
        self._create_load_forecast_table()
        self._create_renewables_forecast_tables()


if __name__ == "__main__":
    db = DatabaseManager()
    schema = SchemaManager(db)
    schema.reset_all_tables()
    print("All tables created successfully.")
    db.close()
