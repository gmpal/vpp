# db/crud.py
from datetime import datetime

import pandas as pd

from backend.src.exceptions import InvalidTableNameError


class CrudManager:
    # Whitelist of valid table names
    VALID_TABLES = {
        # Historical data tables
        "solar",
        "wind",
        "load",
        "market",
        # Forecast tables
        "solar_forecast",
        "wind_forecast",
        "load_forecast",
        "market_forecast",
    }

    def __init__(self, db_manager):
        self.db = db_manager

    def _validate_table_name(self, table: str) -> None:
        """
        Validate that the table name is in the whitelist.

        Args:
            table: Table name to validate

        Raises:
            InvalidTableNameError: If table name is not in whitelist
        """
        if table not in self.VALID_TABLES:
            raise InvalidTableNameError(
                f"Invalid table name: {table}. Must be one of {self.VALID_TABLES}"
            )

    def save_to_db(
        self, table: str, timestamp: datetime, source_id: str | None, value: float
    ):
        self._validate_table_name(table)
        if table in self.db.renewables:
            query = f"INSERT INTO {table} (time, source_id, value) VALUES (%s, %s, %s)"
            self.db.execute(query, (timestamp, source_id, value))
        else:
            query = f"INSERT INTO {table} (time, value) VALUES (%s, %s)"
            self.db.execute(query, (timestamp, value))

    def get_home_evs(self, user_id: str) -> list:
        """Return home EVs for a specific user (via household ownership)."""
        query = """
        SELECT ev.vehicle_id, ev.capacity_kwh, ev.soc_kwh,
               ev.max_charge_kw, ev.max_discharge_kw, ev.eta
        FROM electric_vehicles ev
        JOIN households hh ON ev.household_id = hh.household_id
        WHERE ev.status = 'home' AND hh.user_id = %s
        ORDER BY ev.vehicle_id
        """
        rows = self.db.execute(query, (user_id,), fetch=True) or []
        return [
            {
                "vehicle_id": r[0],
                "capacity_kwh": r[1],
                "soc_kwh": r[2],
                "max_charge_kw": r[3],
                "max_discharge_kw": r[4],
                "eta": r[5],
            }
            for r in rows
        ]

    def save_household_load(self, household_id: str, load_series: pd.Series):
        """Bulk-insert a load time series into household_load."""
        query = (
            "INSERT INTO household_load (time, household_id, value) VALUES (%s, %s, %s)"
        )
        rows = [(ts, household_id, float(v)) for ts, v in load_series.items()]
        with self.db.connect() as conn, conn.cursor() as cursor:
            cursor.executemany(query, rows)
            conn.commit()

    def rebuild_aggregated_load(self):
        """Rebuild the load table as a time-bucketed aggregate of all household_load records.
        Called after any household is created or deleted so the load table stays in sync.
        """
        self.db.execute("DELETE FROM load")
        self.db.execute("""
            INSERT INTO load (time, value)
            SELECT time, SUM(value)
            FROM household_load
            GROUP BY time
            ORDER BY time
        """)

    def load_historical_data(
        self,
        table: str,
        source_id: str | None = None,
        start: str = None,
        end: str = None,
        top: int = None,
    ):
        self._validate_table_name(table)
        params = []
        where_clauses = []
        if source_id:
            where_clauses.append("source_id = %s")
            params.append(source_id)
        if start:
            where_clauses.append("time >= %s")
            params.append(start)
        if end:
            where_clauses.append("time <= %s")
            params.append(end)
        where = " AND ".join(where_clauses) if where_clauses else ""
        query = f"SELECT time, value FROM {table} {'WHERE ' + where if where else ''} ORDER BY time"
        if top:
            query += f" LIMIT {top}"
        rows = self.db.execute(query, params, fetch=True) or []

        # This format is perfect for FastAPI to automatically convert to JSON.
        return [{"time": row[0], "value": row[1]} for row in rows]

    def load_user_historical_data(
        self,
        table: str,
        user_id: str,
        source_id: str | None = None,
        start: str = None,
        end: str = None,
        top: int = None,
    ):
        """Load historical data scoped to a single user.

        - `solar`/`wind`: rows are filtered by the user's registered energy sources.
        - `load`: returned as an aggregate of the user's household_load values by timestamp.
        - `market`: global market series is returned unchanged.
        """
        self._validate_table_name(table)

        params = []
        where_clauses = []

        if table in ("solar", "wind"):
            base_query = f"""
            SELECT t.time, t.value
            FROM {table} t
            JOIN energy_sources es ON t.source_id = es.source_id
            WHERE es.user_id = %s
            """
            params.append(user_id)

            if source_id:
                where_clauses.append("t.source_id = %s")
                params.append(source_id)
            if start:
                where_clauses.append("t.time >= %s")
                params.append(start)
            if end:
                where_clauses.append("t.time <= %s")
                params.append(end)

            if where_clauses:
                base_query += " AND " + " AND ".join(where_clauses)

            query = base_query + " ORDER BY t.time"

        elif table == "load":
            base_query = """
            SELECT hl.time, SUM(hl.value) AS value
            FROM household_load hl
            JOIN households hh ON hl.household_id = hh.household_id
            WHERE hh.user_id = %s
            """
            params.append(user_id)

            if start:
                where_clauses.append("hl.time >= %s")
                params.append(start)
            if end:
                where_clauses.append("hl.time <= %s")
                params.append(end)

            if where_clauses:
                base_query += " AND " + " AND ".join(where_clauses)

            query = base_query + " GROUP BY hl.time ORDER BY hl.time"

        else:
            # Market and any future non-user-specific tables follow existing behavior.
            if source_id:
                where_clauses.append("source_id = %s")
                params.append(source_id)
            if start:
                where_clauses.append("time >= %s")
                params.append(start)
            if end:
                where_clauses.append("time <= %s")
                params.append(end)

            where = " AND ".join(where_clauses) if where_clauses else ""
            query = f"SELECT time, value FROM {table} {'WHERE ' + where if where else ''} ORDER BY time"

        if top:
            query += f" LIMIT {top}"

        rows = self.db.execute(query, params, fetch=True) or []
        return [{"time": row[0], "value": row[1]} for row in rows]

    def save_forecast(
        self, table: str, source_id: str | None, forecasted_df: pd.DataFrame
    ):
        # Validate base table name (table_name will be constructed)
        if table not in ["solar", "load", "market"]:
            raise InvalidTableNameError(
                f"Invalid forecast table base: {table}. Must be one of solar, load, market"
            )
        table_name = f"{table}_forecast"
        self._validate_table_name(table_name)
        columns = ["time"] + (["source_id"] if source_id else []) + ["yhat"]
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
        for time, row in forecasted_df.iterrows():
            values = (
                [time] + ([source_id] if source_id else []) + [float(row["value"])]
            )  # Convert to float
            self.db.execute(query, values)

    def load_forecasted_data(
        self,
        type: str,
        source_id: str | None = None,
        start: str = None,
        end: str = None,
        top: int = None,
    ):
        """
        Retrieves forecasted data for a specific type (e.g., 'solar', 'load') and
        source_id (if applicable) within an optional time range [start, end], with an
        optional limit on rows.

        Args:
            type (str): The type of forecast (e.g., 'solar', 'load').
            source_id (str | None): The source identifier, if applicable (ignored for 'load').
            start (str | None): Start time for filtering (e.g., '2023-01-01').
            end (str | None): End time for filtering (e.g., '2023-12-31').
            top (int | None): Maximum number of rows to return.

        Returns:
            pd.DataFrame: Forecast data with time as the index and yhat (and source_id if applicable).
        """
        # Validate type parameter
        if type not in ["solar", "load", "market"]:
            raise InvalidTableNameError(
                f"Invalid forecast type: {type}. Must be one of solar, load, market"
            )
        table = f"{type}_forecast"
        self._validate_table_name(table)

        params = []
        where_clauses = []

        # Only include source_id for renewables, not load
        if source_id and type in self.db.renewables:
            where_clauses.append("source_id = %s")
            params.append(source_id)
        if start:
            where_clauses.append("time >= %s")
            params.append(start)
        if end:
            where_clauses.append("time <= %s")
            params.append(end)

        where = " AND ".join(where_clauses) if where_clauses else ""

        # Select columns based on type (load_forecast has no source_id)
        if type in self.db.renewables:
            query = f"SELECT time, source_id, yhat FROM {table} {'WHERE ' + where if where else ''} ORDER BY time"
            columns = ["time", "source_id", "yhat"]
        else:  # For 'load'
            query = f"SELECT time, yhat FROM {table} {'WHERE ' + where if where else ''} ORDER BY time"
            columns = ["time", "yhat"]

        if top:
            query += f" LIMIT {top}"

        rows = self.db.execute(query, params, fetch=True) or []

        # Dynamically create the list of dictionaries from the rows and columns
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
        return results

    def query_source_ids(self, source: str, user_id: str = None) -> list[str]:
        self._validate_table_name(source)
        if user_id and source in self.db.renewables:
            query = f"""
            SELECT DISTINCT s.source_id FROM {source} s
            JOIN energy_sources es ON s.source_id = es.source_id
            WHERE es.user_id = %s
            """
            rows = self.db.execute(query, (user_id,), fetch=True) or []
        else:
            query = f"SELECT DISTINCT source_id FROM {source};"
            rows = self.db.execute(query, fetch=True) or []
        return [row[0] for row in rows]

    # --- Household CRUD ---
    def create_household(
        self,
        household_id: str,
        name: str,
        latitude: float,
        longitude: float,
        solar_panels: int = 0,
        building_type: str = "household",
        num_people: int = 1,
        num_evs: int = 0,
        osm_feature_id: str = None,
        user_id: str = None,
        geometry: dict = None,
    ):
        import json

        query = """
        INSERT INTO households (household_id, name, latitude, longitude,
                                solar_panels, building_type, num_people, num_evs,
                                osm_feature_id, user_id, geometry)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (household_id) DO NOTHING
        """
        self.db.execute(
            query,
            (
                household_id,
                name,
                latitude,
                longitude,
                solar_panels,
                building_type,
                num_people,
                num_evs,
                osm_feature_id,
                user_id,
                json.dumps(geometry) if geometry else None,
            ),
        )

    def get_all_households(self, user_id: str) -> list:
        query = """SELECT household_id, name, latitude, longitude,
                          solar_panels, building_type, num_people, num_evs, osm_feature_id, geometry
                   FROM households WHERE user_id = %s ORDER BY created_at DESC"""
        rows = self.db.execute(query, (user_id,), fetch=True) or []
        return [self._household_row_to_dict(r) for r in rows]

    def get_household(self, household_id: str, user_id: str = None) -> dict | None:
        if user_id:
            query = """SELECT household_id, name, latitude, longitude,
                              solar_panels, building_type, num_people, num_evs, osm_feature_id, geometry
                       FROM households WHERE household_id = %s AND user_id = %s"""
            rows = self.db.execute(query, (household_id, user_id), fetch=True) or []
        else:
            query = """SELECT household_id, name, latitude, longitude,
                              solar_panels, building_type, num_people, num_evs, osm_feature_id, geometry
                       FROM households WHERE household_id = %s"""
            rows = self.db.execute(query, (household_id,), fetch=True) or []
        if not rows:
            return None
        return self._household_row_to_dict(rows[0])

    def get_household_by_osm_id(
        self, osm_feature_id: str, user_id: str = None
    ) -> dict | None:
        if user_id:
            query = """SELECT household_id, name, latitude, longitude,
                              solar_panels, building_type, num_people, num_evs, osm_feature_id, geometry
                       FROM households WHERE osm_feature_id = %s AND user_id = %s"""
            rows = self.db.execute(query, (osm_feature_id, user_id), fetch=True) or []
        else:
            query = """SELECT household_id, name, latitude, longitude,
                              solar_panels, building_type, num_people, num_evs, osm_feature_id, geometry
                       FROM households WHERE osm_feature_id = %s"""
            rows = self.db.execute(query, (osm_feature_id,), fetch=True) or []
        if not rows:
            return None
        return self._household_row_to_dict(rows[0])

    def _household_row_to_dict(self, r) -> dict:
        import json

        raw_geom = r[9]
        geometry = json.loads(raw_geom) if isinstance(raw_geom, str) else raw_geom
        return {
            "household_id": r[0],
            "name": r[1],
            "latitude": r[2],
            "longitude": r[3],
            "solar_panels": r[4],
            "building_type": r[5],
            "num_people": r[6],
            "num_evs": r[7],
            "osm_feature_id": r[8],
            "geometry": geometry,
        }

    def delete_household(self, household_id: str):
        self.db.execute(
            "DELETE FROM households WHERE household_id = %s", (household_id,)
        )

    def update_household(self, household_id: str, user_id: str = None, **kwargs):
        import json

        allowed_fields = {
            "name",
            "latitude",
            "longitude",
            "solar_panels",
            "building_type",
            "num_people",
            "num_evs",
            "osm_feature_id",
            "geometry",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return

        if "geometry" in updates:
            updates["geometry"] = (
                json.dumps(updates["geometry"])
                if updates["geometry"] is not None
                else None
            )

        set_clause = ", ".join(f"{field} = %s" for field in updates.keys())
        params = list(updates.values()) + [household_id]
        query = f"UPDATE households SET {set_clause} WHERE household_id = %s"

        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)

        self.db.execute(query, tuple(params))

    # --- EV CRUD ---
    def create_ev(
        self,
        vehicle_id: str,
        household_id: str,
        name: str,
        capacity_kwh: float,
        soc_kwh: float,
        max_charge_kw: float,
        max_discharge_kw: float,
        eta: float,
        status: str = "home",
    ):
        query = """
        INSERT INTO electric_vehicles
        (vehicle_id, household_id, name, capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(
            query,
            (
                vehicle_id,
                household_id,
                name,
                capacity_kwh,
                soc_kwh,
                max_charge_kw,
                max_discharge_kw,
                eta,
                status,
            ),
        )

    def get_all_evs(self, user_id: str) -> list:
        query = """
        SELECT ev.vehicle_id, ev.household_id, ev.name, ev.capacity_kwh, ev.soc_kwh,
               ev.max_charge_kw, ev.max_discharge_kw, ev.eta, ev.status,
               ev.latitude, ev.longitude
        FROM electric_vehicles ev
        JOIN households hh ON ev.household_id = hh.household_id
        WHERE hh.user_id = %s
        ORDER BY ev.created_at DESC
        """
        rows = self.db.execute(query, (user_id,), fetch=True) or []
        return [self._ev_row_to_dict(r) for r in rows]

    def get_evs_by_household(self, household_id: str) -> list:
        query = """
        SELECT vehicle_id, household_id, name, capacity_kwh, soc_kwh,
               max_charge_kw, max_discharge_kw, eta, status, latitude, longitude
        FROM electric_vehicles WHERE household_id = %s ORDER BY created_at DESC
        """
        rows = self.db.execute(query, (household_id,), fetch=True) or []
        return [self._ev_row_to_dict(r) for r in rows]

    def get_ev(self, vehicle_id: str) -> dict | None:
        query = """
        SELECT vehicle_id, household_id, name, capacity_kwh, soc_kwh,
               max_charge_kw, max_discharge_kw, eta, status, latitude, longitude
        FROM electric_vehicles WHERE vehicle_id = %s
        """
        rows = self.db.execute(query, (vehicle_id,), fetch=True) or []
        if not rows:
            return None
        return self._ev_row_to_dict(rows[0])

    def update_ev_soc(self, vehicle_id: str, new_soc: float):
        self.db.execute(
            "UPDATE electric_vehicles SET soc_kwh = %s WHERE vehicle_id = %s",
            (new_soc, vehicle_id),
        )

    def update_ev_status(
        self,
        vehicle_id: str,
        status: str,
        latitude: float = None,
        longitude: float = None,
    ):
        if latitude is not None and longitude is not None:
            self.db.execute(
                "UPDATE electric_vehicles SET status = %s, latitude = %s, longitude = %s WHERE vehicle_id = %s",
                (status, latitude, longitude, vehicle_id),
            )
        else:
            self.db.execute(
                "UPDATE electric_vehicles SET status = %s WHERE vehicle_id = %s",
                (status, vehicle_id),
            )

    def delete_ev(self, vehicle_id: str):
        self.db.execute(
            "DELETE FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,)
        )

    def _ev_row_to_dict(self, r) -> dict:
        return {
            "vehicle_id": r[0],
            "household_id": r[1],
            "name": r[2],
            "capacity_kwh": r[3],
            "soc_kwh": r[4],
            "max_charge_kw": r[5],
            "max_discharge_kw": r[6],
            "eta": r[7],
            "status": r[8],
            "latitude": r[9],
            "longitude": r[10],
        }

    # ---- Battery CRUD ----

    def create_battery(
        self,
        battery_id: str,
        household_id: str,
        name: str,
        capacity_kwh: float,
        soc_kwh: float,
        max_charge_kw: float,
        max_discharge_kw: float,
        eta: float = 0.95,
    ):
        query = """
        INSERT INTO batteries
        (battery_id, household_id, name, capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(
            query,
            (battery_id, household_id, name, capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta),
        )

    def get_all_batteries(self, user_id: str) -> list:
        query = """
        SELECT b.battery_id, b.household_id, b.name, b.capacity_kwh, b.soc_kwh,
               b.max_charge_kw, b.max_discharge_kw, b.eta
        FROM batteries b
        JOIN households hh ON b.household_id = hh.household_id
        WHERE hh.user_id = %s
        ORDER BY b.created_at DESC
        """
        rows = self.db.execute(query, (user_id,), fetch=True) or []
        return [self._battery_row_to_dict(r) for r in rows]

    def get_batteries_by_household(self, household_id: str) -> list:
        query = """
        SELECT battery_id, household_id, name, capacity_kwh, soc_kwh,
               max_charge_kw, max_discharge_kw, eta
        FROM batteries WHERE household_id = %s ORDER BY created_at DESC
        """
        rows = self.db.execute(query, (household_id,), fetch=True) or []
        return [self._battery_row_to_dict(r) for r in rows]

    def get_battery(self, battery_id: str) -> dict | None:
        query = """
        SELECT battery_id, household_id, name, capacity_kwh, soc_kwh,
               max_charge_kw, max_discharge_kw, eta
        FROM batteries WHERE battery_id = %s
        """
        rows = self.db.execute(query, (battery_id,), fetch=True) or []
        if not rows:
            return None
        return self._battery_row_to_dict(rows[0])

    def get_home_batteries(self, user_id: str) -> list:
        """Return all batteries for a user (batteries are always 'home')."""
        query = """
        SELECT b.battery_id, b.capacity_kwh, b.soc_kwh,
               b.max_charge_kw, b.max_discharge_kw, b.eta
        FROM batteries b
        JOIN households hh ON b.household_id = hh.household_id
        WHERE hh.user_id = %s
        ORDER BY b.battery_id
        """
        rows = self.db.execute(query, (user_id,), fetch=True) or []
        return [
            {
                "vehicle_id": r[0],  # reuse vehicle_id key for optimizer compatibility
                "capacity_kwh": r[1],
                "soc_kwh": r[2],
                "max_charge_kw": r[3],
                "max_discharge_kw": r[4],
                "eta": r[5],
            }
            for r in rows
        ]

    def update_battery_soc(self, battery_id: str, new_soc: float):
        self.db.execute(
            "UPDATE batteries SET soc_kwh = %s WHERE battery_id = %s",
            (new_soc, battery_id),
        )

    def delete_battery(self, battery_id: str):
        self.db.execute(
            "DELETE FROM batteries WHERE battery_id = %s", (battery_id,)
        )

    def _battery_row_to_dict(self, r) -> dict:
        return {
            "battery_id": r[0],
            "household_id": r[1],
            "name": r[2],
            "capacity_kwh": r[3],
            "soc_kwh": r[4],
            "max_charge_kw": r[5],
            "max_discharge_kw": r[6],
            "eta": r[7],
        }

    def get_community_summary(self, user_id: str) -> dict:
        """Returns aggregated production, consumption and EV state for the whole community."""
        # Latest solar production sum — scoped to user's sources
        solar_query = """
        SELECT COALESCE(SUM(latest.value), 0)
        FROM (
            SELECT DISTINCT ON (s.source_id) s.value
            FROM solar s
            JOIN energy_sources es ON s.source_id = es.source_id
            WHERE es.user_id = %s
            ORDER BY s.source_id, s.time DESC
        ) latest
        """
        solar_rows = self.db.execute(solar_query, (user_id,), fetch=True) or [(0,)]
        total_solar = float(solar_rows[0][0])

        # Latest wind production sum — scoped to user's sources
        wind_query = """
        SELECT COALESCE(SUM(latest.value), 0)
        FROM (
            SELECT DISTINCT ON (w.source_id) w.value
            FROM wind w
            JOIN energy_sources es ON w.source_id = es.source_id
            WHERE es.user_id = %s
            ORDER BY w.source_id, w.time DESC
        ) latest
        """
        wind_rows = self.db.execute(wind_query, (user_id,), fetch=True) or [(0,)]
        total_wind = float(wind_rows[0][0])

        # Rooftop production estimate from building panel count.
        # This keeps community production responsive when users add buildings with panels.
        rooftop_query = """
        SELECT COALESCE(SUM(GREATEST(solar_panels, 0)), 0)
        FROM households
        WHERE user_id = %s
        """
        rooftop_rows = self.db.execute(rooftop_query, (user_id,), fetch=True) or [(0,)]
        total_panels = float(rooftop_rows[0][0])
        estimated_rooftop_kw = total_panels * 0.35

        total_production = total_solar + total_wind + estimated_rooftop_kw

        # Latest load — sum of each household's most recent value, scoped to this user
        load_query = """
        SELECT COALESCE(SUM(latest.value), 0)
        FROM (
            SELECT DISTINCT ON (hl.household_id) hl.value
            FROM household_load hl
            JOIN households hh ON hl.household_id = hh.household_id
            WHERE hh.user_id = %s
            ORDER BY hl.household_id, hl.time DESC
        ) latest
        """
        load_rows = self.db.execute(load_query, (user_id,), fetch=True) or [(0,)]
        total_consumption = float(load_rows[0][0])

        # EV SOC aggregation — scoped to user's households
        ev_query = """
        SELECT COALESCE(SUM(ev.soc_kwh), 0), COALESCE(SUM(ev.capacity_kwh), 0), COUNT(*)
        FROM electric_vehicles ev
        JOIN households hh ON ev.household_id = hh.household_id
        WHERE hh.user_id = %s
        """
        ev_rows = self.db.execute(ev_query, (user_id,), fetch=True) or [(0, 0, 0)]
        ev_soc_total = float(ev_rows[0][0])
        ev_soc_capacity = float(ev_rows[0][1])
        ev_count = int(ev_rows[0][2])

        # Battery SOC aggregation — scoped to user's households
        battery_query = """
        SELECT COALESCE(SUM(b.soc_kwh), 0), COALESCE(SUM(b.capacity_kwh), 0), COUNT(*)
        FROM batteries b
        JOIN households hh ON b.household_id = hh.household_id
        WHERE hh.user_id = %s
        """
        bat_rows = self.db.execute(battery_query, (user_id,), fetch=True) or [(0, 0, 0)]
        battery_soc_total = float(bat_rows[0][0])
        battery_soc_capacity = float(bat_rows[0][1])
        battery_count = int(bat_rows[0][2])

        # Household count — scoped to user
        hh_query = "SELECT COUNT(*) FROM households WHERE user_id = %s"
        hh_rows = self.db.execute(hh_query, (user_id,), fetch=True) or [(0,)]
        household_count = int(hh_rows[0][0])

        total_storage_soc = ev_soc_total + battery_soc_total
        total_storage_capacity = ev_soc_capacity + battery_soc_capacity
        total_storage_count = ev_count + battery_count

        net = total_production - total_consumption
        if net > 0.1:
            action = "selling"
        elif net < -0.1 and total_storage_count > 0 and total_storage_soc < total_storage_capacity * 0.9:
            action = "charging_evs"
        elif net < -0.1:
            action = "buying"
        else:
            action = "self_sufficient"

        return {
            "total_production": total_production,
            "total_consumption": total_consumption,
            "net": net,
            "ev_soc_total": ev_soc_total,
            "ev_soc_capacity": ev_soc_capacity,
            "battery_soc_total": battery_soc_total,
            "battery_soc_capacity": battery_soc_capacity,
            "action": action,
            "household_count": household_count,
            "ev_count": ev_count,
            "battery_count": battery_count,
        }
