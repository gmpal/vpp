# db/crud.py
import pandas as pd
from src.battery import Battery


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
        query = f"SELECT time, value FROM {table} {'WHERE ' + where if where else ''} ORDER BY time DESC"
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
        columns = (
            ["time"]
            + (["source_id"] if source_id else [])
            + [
                "trend",
                "yhat_lower",
                "yhat_upper",
                "trend_lower",
                "trend_upper",
                "additive_terms",
                "additive_terms_lower",
                "additive_terms_upper",
                "daily",
                "daily_lower",
                "daily_upper",
                "multiplicative_terms",
                "multiplicative_terms_lower",
                "multiplicative_terms_upper",
                "yhat",
            ]
        )
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"
        for time, row in forecasted_df.iterrows():
            values = [time] + ([source_id] if source_id else []) + [row["value"]]
            self.db.execute(query, values)

    def query_source_ids(self, source: str) -> list[str]:
        query = f"SELECT DISTINCT source_id FROM {source};"
        rows = self.db.execute(query, fetch=True) or []
        return [row[0] for row in rows]
