# db/crud.py
from datetime import datetime
import pandas as pd
from backend.src.exceptions import InvalidTableNameError


class CrudManager:
    # Whitelist of valid table names
    VALID_TABLES = {
        # Historical data tables
        "solar", "load", "market",
        # Forecast tables
        "solar_forecast", "load_forecast", "market_forecast"
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

    def get_home_evs(self) -> list:
        """Return all EVs currently at home as dicts (usable as Battery proxies)."""
        query = """
        SELECT vehicle_id, capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta
        FROM electric_vehicles
        WHERE status = 'home'
        ORDER BY vehicle_id
        """
        rows = self.db.execute(query, fetch=True) or []
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
        query = "INSERT INTO household_load (time, household_id, value) VALUES (%s, %s, %s)"
        for timestamp, value in load_series.items():
            self.db.execute(query, (timestamp, household_id, float(value)))

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

    def query_source_ids(self, source: str) -> list[str]:
        self._validate_table_name(source)
        query = f"SELECT DISTINCT source_id FROM {source};"
        rows = self.db.execute(query, fetch=True) or []
        return [row[0] for row in rows]

    # --- Household CRUD ---
    def create_household(self, household_id: str, name: str, latitude: float, longitude: float,
                         solar_panels: int = 0, building_type: str = 'household',
                         num_people: int = 1, num_evs: int = 0, osm_feature_id: str = None):
        query = """
        INSERT INTO households (household_id, name, latitude, longitude,
                                solar_panels, building_type, num_people, num_evs, osm_feature_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (household_id) DO NOTHING
        """
        self.db.execute(query, (household_id, name, latitude, longitude,
                                solar_panels, building_type, num_people, num_evs, osm_feature_id))

    def get_all_households(self) -> list:
        query = """SELECT household_id, name, latitude, longitude,
                          solar_panels, building_type, num_people, num_evs, osm_feature_id
                   FROM households ORDER BY created_at DESC"""
        rows = self.db.execute(query, fetch=True) or []
        return [self._household_row_to_dict(r) for r in rows]

    def get_household(self, household_id: str) -> dict | None:
        query = """SELECT household_id, name, latitude, longitude,
                          solar_panels, building_type, num_people, num_evs, osm_feature_id
                   FROM households WHERE household_id = %s"""
        rows = self.db.execute(query, (household_id,), fetch=True) or []
        if not rows:
            return None
        return self._household_row_to_dict(rows[0])

    def get_household_by_osm_id(self, osm_feature_id: str) -> dict | None:
        query = """SELECT household_id, name, latitude, longitude,
                          solar_panels, building_type, num_people, num_evs, osm_feature_id
                   FROM households WHERE osm_feature_id = %s"""
        rows = self.db.execute(query, (osm_feature_id,), fetch=True) or []
        if not rows:
            return None
        return self._household_row_to_dict(rows[0])

    def _household_row_to_dict(self, r) -> dict:
        return {
            "household_id": r[0], "name": r[1], "latitude": r[2], "longitude": r[3],
            "solar_panels": r[4], "building_type": r[5], "num_people": r[6],
            "num_evs": r[7], "osm_feature_id": r[8],
        }

    def delete_household(self, household_id: str):
        self.db.execute("DELETE FROM households WHERE household_id = %s", (household_id,))

    # --- EV CRUD ---
    def create_ev(self, vehicle_id: str, household_id: str, name: str, capacity_kwh: float,
                  soc_kwh: float, max_charge_kw: float, max_discharge_kw: float, eta: float,
                  status: str = 'home'):
        query = """
        INSERT INTO electric_vehicles
        (vehicle_id, household_id, name, capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(query, (vehicle_id, household_id, name, capacity_kwh, soc_kwh,
                                 max_charge_kw, max_discharge_kw, eta, status))

    def get_all_evs(self) -> list:
        query = """
        SELECT vehicle_id, household_id, name, capacity_kwh, soc_kwh,
               max_charge_kw, max_discharge_kw, eta, status, latitude, longitude
        FROM electric_vehicles ORDER BY created_at DESC
        """
        rows = self.db.execute(query, fetch=True) or []
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
        self.db.execute("UPDATE electric_vehicles SET soc_kwh = %s WHERE vehicle_id = %s", (new_soc, vehicle_id))

    def update_ev_status(self, vehicle_id: str, status: str, latitude: float = None, longitude: float = None):
        if latitude is not None and longitude is not None:
            self.db.execute(
                "UPDATE electric_vehicles SET status = %s, latitude = %s, longitude = %s WHERE vehicle_id = %s",
                (status, latitude, longitude, vehicle_id)
            )
        else:
            self.db.execute("UPDATE electric_vehicles SET status = %s WHERE vehicle_id = %s", (status, vehicle_id))

    def delete_ev(self, vehicle_id: str):
        self.db.execute("DELETE FROM electric_vehicles WHERE vehicle_id = %s", (vehicle_id,))

    def _ev_row_to_dict(self, r) -> dict:
        return {
            "vehicle_id": r[0], "household_id": r[1], "name": r[2],
            "capacity_kwh": r[3], "soc_kwh": r[4],
            "max_charge_kw": r[5], "max_discharge_kw": r[6],
            "eta": r[7], "status": r[8], "latitude": r[9], "longitude": r[10]
        }

    def get_community_summary(self) -> dict:
        """Returns aggregated production, consumption and EV state for the whole community."""
        # Latest solar production sum
        solar_query = """
        SELECT COALESCE(SUM(latest.value), 0)
        FROM (
            SELECT DISTINCT ON (source_id) value
            FROM solar ORDER BY source_id, time DESC
        ) latest
        """
        solar_rows = self.db.execute(solar_query, fetch=True) or [(0,)]
        total_solar = float(solar_rows[0][0])

        total_production = total_solar

        # Latest load
        load_query = "SELECT COALESCE(value, 0) FROM load ORDER BY time DESC LIMIT 1"
        load_rows = self.db.execute(load_query, fetch=True) or [(0,)]
        total_consumption = float(load_rows[0][0])

        # EV SOC aggregation
        ev_query = "SELECT COALESCE(SUM(soc_kwh), 0), COALESCE(SUM(capacity_kwh), 0), COUNT(*) FROM electric_vehicles"
        ev_rows = self.db.execute(ev_query, fetch=True) or [(0, 0, 0)]
        ev_soc_total = float(ev_rows[0][0])
        ev_soc_capacity = float(ev_rows[0][1])
        ev_count = int(ev_rows[0][2])

        # Household count
        hh_query = "SELECT COUNT(*) FROM households"
        hh_rows = self.db.execute(hh_query, fetch=True) or [(0,)]
        household_count = int(hh_rows[0][0])

        net = total_production - total_consumption
        if net > 0.1:
            action = "selling"
        elif net < -0.1 and ev_count > 0 and ev_soc_total < ev_soc_capacity * 0.9:
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
            "action": action,
            "household_count": household_count,
            "ev_count": ev_count,
        }
