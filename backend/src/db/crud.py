# db/crud.py
import pandas as pd
from backend.src.storage.battery import Battery


class CrudManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def save_to_db(
        self, table: str, timestamp: pd.Timestamp, source_id: str | None, value: float
    ):
        if table in self.db.renewables:
            query = f"INSERT INTO {table} (time, source_id, value) VALUES (%s, %s, %s)"
            self.db.execute(query, (timestamp, source_id, value))
        else:
            query = f"INSERT INTO {table} (time, value) VALUES (%s, %s)"
            self.db.execute(query, (timestamp, value))

    def save_battery_state(self, battery: Battery):
        timestamp = pd.Timestamp.now()
        delete_query = "DELETE FROM batteries WHERE battery_id = %s"
        self.db.execute(delete_query, (battery.battery_id,))
        query = """
        INSERT INTO batteries 
        (time, battery_id, capacity_kWh, soc_kWh, max_charge_kW, max_discharge_kW, eta)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(
            query,
            (
                timestamp,
                battery.battery_id,
                battery.capacity_kWh,
                battery.current_soc_kWh,
                battery.max_charge_kW,
                battery.max_discharge_kW,
                battery.round_trip_efficiency,
            ),
        )

    def load_historical_data(
        self,
        table: str,
        source_id: str | None = None,
        start: str = None,
        end: str = None,
        top: int = None,
    ):
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
        df = pd.DataFrame(rows, columns=["time", "value"]).set_index("time")
        df.index = pd.to_datetime(df.index)
        return df

    def save_forecast(
        self, table: str, source_id: str | None, forecasted_df: pd.DataFrame
    ):
        table_name = f"{table}_forecast"
        columns = ["time"] + (["source_id"] if source_id else []) + ["yhat"]
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
        for time, row in forecasted_df.iterrows():
            values = [time] + ([source_id] if source_id else []) + [row["value"]]
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
        Retrieves forecasted data for a specific type (e.g., 'solar', 'wind', 'load') and
        source_id (if applicable) within an optional time range [start, end], with an
        optional limit on rows.

        Args:
            type (str): The type of forecast (e.g., 'solar', 'wind', 'load').
            source_id (str | None): The source identifier, if applicable (ignored for 'load').
            start (str | None): Start time for filtering (e.g., '2023-01-01').
            end (str | None): End time for filtering (e.g., '2023-12-31').
            top (int | None): Maximum number of rows to return.

        Returns:
            pd.DataFrame: Forecast data with time as the index and yhat (and source_id if applicable).
        """
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
        table = f"{type}_forecast"

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

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=columns)
        if not df.empty:
            df["time"] = pd.to_datetime(df["time"])
            df.set_index("time", inplace=True)

        return df

    def query_source_ids(self, source: str) -> list[str]:
        query = f"SELECT DISTINCT source_id FROM {source};"
        rows = self.db.execute(query, fetch=True) or []
        return [row[0] for row in rows]
