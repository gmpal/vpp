import configparser
import psycopg2
import os
import json
import time
import pandas as pd
from kafka import KafkaProducer

from psycopg2.extras import execute_values

from multiprocessing import Process
from src.battery import Battery


RENEWABLES = ["solar", "wind"]  # scalable for more renewables
OTHER_DATASETS = ["load", "market"]


def reset_all_forecast_tables():
    """
    Drops and recreates all forecast tables for renewable sources (as defined in RENEWABLES),
    as well as for load and market data. Each table is converted into a hypertable.
    """
    conn = _connect()
    cursor = conn.cursor()

    queries = []

    # Reset forecast tables for each renewable (e.g., solar_forecast, wind_forecast, etc.)
    for renewable in RENEWABLES:
        renewable_forecast_query = f"""
            DROP TABLE IF EXISTS {renewable}_forecast;
            CREATE TABLE {renewable}_forecast (
                time TIMESTAMPTZ NOT NULL,
                source_id VARCHAR(50),
                trend DOUBLE PRECISION,
                yhat_lower DOUBLE PRECISION,
                yhat_upper DOUBLE PRECISION,
                trend_lower DOUBLE PRECISION,
                trend_upper DOUBLE PRECISION,
                additive_terms DOUBLE PRECISION,
                additive_terms_lower DOUBLE PRECISION,
                additive_terms_upper DOUBLE PRECISION,
                daily DOUBLE PRECISION,
                daily_lower DOUBLE PRECISION,
                daily_upper DOUBLE PRECISION,
                multiplicative_terms DOUBLE PRECISION,
                multiplicative_terms_lower DOUBLE PRECISION,
                multiplicative_terms_upper DOUBLE PRECISION,
                yhat DOUBLE PRECISION
            );
            SELECT create_hypertable('{renewable}_forecast', 'time');
        """
        queries.append(renewable_forecast_query)

    # Reset the forecast table for load
    load_forecast_query = """
        DROP TABLE IF EXISTS load_forecast;
        CREATE TABLE load_forecast (
            time TIMESTAMPTZ NOT NULL,
            trend DOUBLE PRECISION,
            yhat_lower DOUBLE PRECISION,
            yhat_upper DOUBLE PRECISION,
            trend_lower DOUBLE PRECISION,
            trend_upper DOUBLE PRECISION,
            additive_terms DOUBLE PRECISION,
            additive_terms_lower DOUBLE PRECISION,
            additive_terms_upper DOUBLE PRECISION,
            daily DOUBLE PRECISION,
            daily_lower DOUBLE PRECISION,
            daily_upper DOUBLE PRECISION,
            multiplicative_terms DOUBLE PRECISION,
            multiplicative_terms_lower DOUBLE PRECISION,
            multiplicative_terms_upper DOUBLE PRECISION,
            yhat DOUBLE PRECISION
        );
        SELECT create_hypertable('load_forecast', 'time');
    """
    queries.append(load_forecast_query)

    # Reset the forecast table for market
    market_forecast_query = """
        DROP TABLE IF EXISTS market_forecast;
        CREATE TABLE market_forecast (
            time TIMESTAMPTZ NOT NULL,
            trend DOUBLE PRECISION,
            yhat_lower DOUBLE PRECISION,
            yhat_upper DOUBLE PRECISION,
            trend_lower DOUBLE PRECISION,
            trend_upper DOUBLE PRECISION,
            additive_terms DOUBLE PRECISION,
            additive_terms_lower DOUBLE PRECISION,
            additive_terms_upper DOUBLE PRECISION,
            daily DOUBLE PRECISION,
            daily_lower DOUBLE PRECISION,
            daily_upper DOUBLE PRECISION,
            multiplicative_terms DOUBLE PRECISION,
            multiplicative_terms_lower DOUBLE PRECISION,
            multiplicative_terms_upper DOUBLE PRECISION,
            yhat DOUBLE PRECISION
        );
        SELECT create_hypertable('market_forecast', 'time');
    """
    queries.append(market_forecast_query)

    # Execute all queries in sequence
    for query in queries:
        cursor.execute(query)
        conn.commit()
        print("Executed query:", query.split("\n")[1].strip(), flush=True)

    cursor.close()
    conn.close()
    print("All forecast tables reset.", flush=True)


def kafka_produce(producer_info: tuple, sleeping_time: int = 60):
    """
    TODO: temporarely duplicated to avoid circular import
    Produces messages to a Kafka topic.
    Args:
        producer_info (tuple): A tuple containing the topic name (str), source ID (str),
                               and a DataFrame (pandas.DataFrame) with the data to be sent.
        sleeping_time (int): The time to sleep between sending messages. Defaults to 60. Units: seconds.
    The DataFrame should have a datetime index and a single column of values. Each row in the
    DataFrame will be sent as a separate message to the specified Kafka topic.
    The function serializes the message as JSON and sends it to the Kafka topic with a delay
    of 5 seconds between each message.
    Example:
        producer_info = ("my_topic", "source_1", df)
        kafka_produce(producer_info)
    """

    topic, source_id, df = producer_info

    producer = KafkaProducer(
        bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    for _, row in df.iterrows():
        message = {"source_id": source_id, "timestamp": row.name, "data": row.values[0]}
        producer.send(topic, value=message, partition=0)
        print(
            f"Message from {source_id} at {row.name} sent to topic {topic} with value {row.values[0]}"
        )
        time.sleep(sleeping_time)


def _connect():
    # ------------------------------
    # 1. Read database config
    # ------------------------------
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Use environment variables if available; otherwise, fallback to config.ini
    db_connection_info = {
        "dbname": os.environ.get("POSTGRES_DB", config["TimescaleDB"]["dbname"]),
        "user": os.environ.get("POSTGRES_USER", config["TimescaleDB"]["user"]),
        "password": os.environ.get(
            "POSTGRES_PASSWORD", config["TimescaleDB"]["password"]
        ),
        "host": os.environ.get("TIMESCALEDB_HOST", config["TimescaleDB"]["host"]),
        "port": os.environ.get("POSTGRES_PORT", config["TimescaleDB"]["port"]),
    }

    conn = psycopg2.connect(**db_connection_info)

    return conn


def _reset_all_tables_in_public(cursor):
    """
    Drops all tables in the public schema, if they exist.
    This does not remove the schema itself or any extensions.
    """
    drop_all_tables = """
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
    cursor.execute(drop_all_tables)


def reset_tables():
    """
    Resets the database tables for renewable energy sources, load, and market price.
    This function connects to the database, drops existing tables if they exist,
    and creates new tables for each renewable energy source defined in the RENEWABLES
    list, as well as for load and market price data. It does the same for forecasted values.
    It also converts these tables into hypertables using the TimescaleDB extension.
    The tables created are:
    - Renewable energy sources (one table per source in RENEWABLES)
    - Renewable energy sources forecasted (one table per source in RENEWABLES)
    - Load
    - Load forecasted
    - Market price
    - Market price forecasted
    Each table has the following columns:
    - time: TIMESTAMPTZ (timestamp with time zone), not null
    - source_id: VARCHAR(50) (only for renewable energy sources)
    - value: DOUBLE PRECISION
    For forecasted tables, the columns are:
    - time: TIMESTAMPTZ (timestamp with time zone), not null
    - source_id: VARCHAR(50) (only for renewable energy sources)
    - forecast: DOUBLE PRECISION
    - lower: DOUBLE PRECISION
    - upper: DOUBLE PRECISION

    Note:
    - The function assumes that the `connect` function and `RENEWABLES` list are
      defined elsewhere in the code.
    - The function commits each query to the database immediately after execution.
    Raises:
    - Any exceptions raised by the database connection or cursor execution will
      propagate up to the caller.
    """

    conn = _connect()
    cursor = conn.cursor()

    _reset_all_tables_in_public(cursor)
    conn.commit()

    queries = []

    battery_query = """
    DROP TABLE IF EXISTS batteries;
    CREATE TABLE batteries (
        time             TIMESTAMPTZ NOT NULL,
        battery_id       VARCHAR(50),
        capacity_kWh     DOUBLE PRECISION,
        soc_kWh          DOUBLE PRECISION,
        max_charge_kW    DOUBLE PRECISION,
        max_discharge_kW DOUBLE PRECISION,
        eta              DOUBLE PRECISION
    );
    SELECT create_hypertable('batteries', 'time');
    """
    queries.append(battery_query)

    for renewable in RENEWABLES:

        renewable_query = f"""
        DROP TABLE IF EXISTS {renewable};
        CREATE TABLE {renewable} (
            time        TIMESTAMPTZ NOT NULL,
            source_id   VARCHAR(50),
            value       DOUBLE PRECISION
        );
        SELECT create_hypertable('{renewable}', 'time');
        """

        queries.append(renewable_query)

        renewable_forecast_query = f"""
        DROP TABLE IF EXISTS {renewable}_forecast;
        CREATE TABLE {renewable}_forecast (
            time        TIMESTAMPTZ NOT NULL,
            source_id   VARCHAR(50),
            trend       DOUBLE PRECISION,
            yhat_lower  DOUBLE PRECISION,
            yhat_upper  DOUBLE PRECISION,
            trend_lower DOUBLE PRECISION,
            trend_upper DOUBLE PRECISION,
            additive_terms DOUBLE PRECISION,
            additive_terms_lower DOUBLE PRECISION,
            additive_terms_upper DOUBLE PRECISION,
            daily DOUBLE PRECISION,
            daily_lower DOUBLE PRECISION,
            daily_upper DOUBLE PRECISION,
            multiplicative_terms DOUBLE PRECISION,
            multiplicative_terms_lower DOUBLE PRECISION,
            multiplicative_terms_upper DOUBLE PRECISION,
            yhat DOUBLE PRECISION
        );
        SELECT create_hypertable('{renewable}_forecast', 'time');
        """

        queries.append(renewable_forecast_query)

    load_query = """
    DROP TABLE IF EXISTS load;
    CREATE TABLE load (
        time        TIMESTAMPTZ NOT NULL,
        value       DOUBLE PRECISION
    );
    SELECT create_hypertable('load', 'time');
    """

    queries.append(load_query)

    load_forecast_query = """
    DROP TABLE IF EXISTS load_forecast;
    CREATE TABLE load_forecast (
        time        TIMESTAMPTZ NOT NULL,
        trend       DOUBLE PRECISION,
        yhat_lower  DOUBLE PRECISION,
        yhat_upper  DOUBLE PRECISION,
        trend_lower DOUBLE PRECISION,
        trend_upper DOUBLE PRECISION,
        additive_terms DOUBLE PRECISION,
        additive_terms_lower DOUBLE PRECISION,
        additive_terms_upper DOUBLE PRECISION,
        daily DOUBLE PRECISION,
        daily_lower DOUBLE PRECISION,
        daily_upper DOUBLE PRECISION,
        multiplicative_terms DOUBLE PRECISION,
        multiplicative_terms_lower DOUBLE PRECISION,
        multiplicative_terms_upper DOUBLE PRECISION,
        yhat DOUBLE PRECISION
    );
    SELECT create_hypertable('load_forecast', 'time');
    """

    queries.append(load_forecast_query)

    price_query = """
    DROP TABLE IF EXISTS market;
    CREATE TABLE market (
        time        TIMESTAMPTZ NOT NULL,
        value       DOUBLE PRECISION
    );
    SELECT create_hypertable('market', 'time');
    """

    queries.append(price_query)

    price_forecast_query = """
    DROP TABLE IF EXISTS market_forecast;
    CREATE TABLE market_forecast (
        time        TIMESTAMPTZ NOT NULL,
        trend       DOUBLE PRECISION,
        yhat_lower  DOUBLE PRECISION,
        yhat_upper  DOUBLE PRECISION,
        trend_lower DOUBLE PRECISION,
        trend_upper DOUBLE PRECISION,
        additive_terms DOUBLE PRECISION,
        additive_terms_lower DOUBLE PRECISION,
        additive_terms_upper DOUBLE PRECISION,
        daily DOUBLE PRECISION,
        daily_lower DOUBLE PRECISION,
        daily_upper DOUBLE PRECISION,
        multiplicative_terms DOUBLE PRECISION,
        multiplicative_terms_lower DOUBLE PRECISION,
        multiplicative_terms_upper DOUBLE PRECISION,
        yhat DOUBLE PRECISION
    );
    SELECT create_hypertable('market_forecast', 'time');
    """

    queries.append(price_forecast_query)

    for query in queries:
        cursor.execute(query)
        conn.commit()

    cursor.close()

    conn.close()


def reset_forecast_tables():
    """
    Resets only the forecast tables for each renewable energy source,
    as well as for load and market. It leaves existing (non-forecast)
    tables untouched.

    The tables dropped and recreated here are:
    - {renewable}_forecast  (for each renewable in RENEWABLES)
    - load_forecast
    - market_forecast

    Each forecast table is recreated with columns corresponding to
    Prophet output (time, trend, yhat, confidence intervals, etc.),
    and converted into a hypertable using TimescaleDB.

    Note:
    - The function assumes that the `_connect()` function and the
      `RENEWABLES` list are defined elsewhere in the code.
    - Any exceptions raised by the database connection or cursor
      execution will propagate up to the caller.
    """

    conn = _connect()
    cursor = conn.cursor()

    queries = []

    # Recreate forecast tables for each renewable
    for renewable in RENEWABLES:
        renewable_forecast_query = f"""
        DROP TABLE IF EXISTS {renewable}_forecast;
        CREATE TABLE {renewable}_forecast (
            time        TIMESTAMPTZ NOT NULL,
            source_id   VARCHAR(50),
            trend       DOUBLE PRECISION,
            yhat_lower  DOUBLE PRECISION,
            yhat_upper  DOUBLE PRECISION,
            trend_lower DOUBLE PRECISION,
            trend_upper DOUBLE PRECISION,
            additive_terms DOUBLE PRECISION,
            additive_terms_lower DOUBLE PRECISION,
            additive_terms_upper DOUBLE PRECISION,
            daily DOUBLE PRECISION,
            daily_lower DOUBLE PRECISION,
            daily_upper DOUBLE PRECISION,
            multiplicative_terms DOUBLE PRECISION,
            multiplicative_terms_lower DOUBLE PRECISION,
            multiplicative_terms_upper DOUBLE PRECISION,
            yhat DOUBLE PRECISION
        );
        SELECT create_hypertable('{renewable}_forecast', 'time');
        """
        queries.append(renewable_forecast_query)

    # Recreate forecast table for load
    load_forecast_query = """
    DROP TABLE IF EXISTS load_forecast;
    CREATE TABLE load_forecast (
        time        TIMESTAMPTZ NOT NULL,
        trend       DOUBLE PRECISION,
        yhat_lower  DOUBLE PRECISION,
        yhat_upper  DOUBLE PRECISION,
        trend_lower DOUBLE PRECISION,
        trend_upper DOUBLE PRECISION,
        additive_terms DOUBLE PRECISION,
        additive_terms_lower DOUBLE PRECISION,
        additive_terms_upper DOUBLE PRECISION,
        daily DOUBLE PRECISION,
        daily_lower DOUBLE PRECISION,
        daily_upper DOUBLE PRECISION,
        multiplicative_terms DOUBLE PRECISION,
        multiplicative_terms_lower DOUBLE PRECISION,
        multiplicative_terms_upper DOUBLE PRECISION,
        yhat DOUBLE PRECISION
    );
    SELECT create_hypertable('load_forecast', 'time');
    """
    queries.append(load_forecast_query)

    # Recreate forecast table for market
    market_forecast_query = """
    DROP TABLE IF EXISTS market_forecast;
    CREATE TABLE market_forecast (
        time        TIMESTAMPTZ NOT NULL,
        trend       DOUBLE PRECISION,
        yhat_lower  DOUBLE PRECISION,
        yhat_upper  DOUBLE PRECISION,
        trend_lower DOUBLE PRECISION,
        trend_upper DOUBLE PRECISION,
        additive_terms DOUBLE PRECISION,
        additive_terms_lower DOUBLE PRECISION,
        additive_terms_upper DOUBLE PRECISION,
        daily DOUBLE PRECISION,
        daily_lower DOUBLE PRECISION,
        daily_upper DOUBLE PRECISION,
        multiplicative_terms DOUBLE PRECISION,
        multiplicative_terms_lower DOUBLE PRECISION,
        multiplicative_terms_upper DOUBLE PRECISION,
        yhat DOUBLE PRECISION
    );
    SELECT create_hypertable('market_forecast', 'time');
    """
    queries.append(market_forecast_query)

    # Execute each drop/create in turn
    for query in queries:
        cursor.execute(query)
        conn.commit()

    cursor.close()
    conn.close()


def load_from_db():
    """
    TODO: allow flexible loading of data from the database (time filtering)

    Connects to the database, loads data for each renewable source, load data and market price data.
    Returns:
        dict: A dictionary with renewables data nested by renewable type and source_id,
              and separate keys for load and market time series.
    Raises:
        psycopg2.DatabaseError: If there is an error while interacting with the database.
    """
    conn = _connect()
    cursor = conn.cursor()

    result = {"renewables": {}, "load": None, "market": None}

    # Load renewable data and store as Pandas Series
    for renewable in RENEWABLES:
        # Initialize nested dictionary for each renewable type
        result["renewables"][renewable] = {}

        # Query to fetch all data for the renewable type
        query = f"SELECT time, source_id, value FROM {renewable} ORDER BY time;"
        cursor.execute(query)
        rows = cursor.fetchall()

        # If there is data, convert to DataFrame for easier grouping; else skip
        if rows:
            df = pd.DataFrame(rows, columns=["time", "source_id", "value"])

            # Group by source_id and create a Series for each group
            for source_id, group in df.groupby("source_id"):
                # Create a Series: index as time, values as value
                series = pd.Series(
                    data=group["value"].values, index=pd.to_datetime(group["time"])
                )
                result["renewables"][renewable][source_id] = series

    # Load 'load' data
    query_load = "SELECT time, value FROM load ORDER BY time;"
    cursor.execute(query_load)
    load_rows = cursor.fetchall()
    if load_rows:
        df_load = pd.DataFrame(load_rows, columns=["time", "value"])
        result["load"] = pd.Series(
            data=df_load["value"].values, index=pd.to_datetime(df_load["time"])
        )

    # Load 'market' data
    query_price = "SELECT time, value FROM market ORDER BY time;"
    cursor.execute(query_price)
    price_rows = cursor.fetchall()
    if price_rows:
        df_price = pd.DataFrame(price_rows, columns=["time", "value"])
        result["market"] = pd.Series(
            data=df_price["value"].values, index=pd.to_datetime(df_price["time"])
        )

    cursor.close()
    conn.close()

    return result


def save_battery_state(battery: Battery):
    """
    Save the current state of a battery into the batteries table.

    Parameters:
    - battery_id: Identifier for the battery.
    - timestamp: The time at which the state is recorded.
    - battery: An instance of the Battery class.
    """
    conn = _connect()
    cursor = conn.cursor()
    timestamp = pd.Timestamp.now()

    # We only keep the latest state of the battery
    delete_query = "DELETE FROM batteries WHERE battery_id = %s"
    cursor.execute(delete_query, (battery.battery_id,))

    query = """
    INSERT INTO batteries 
    (time, battery_id, capacity_kWh, soc_kWh, max_charge_kW, max_discharge_kW, eta)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(
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

    conn.commit()
    cursor.close()
    conn.close()


def save_to_db(topic: str, timestamp: pd.DatetimeIndex, source_id: str, value: float):
    """
    Assumes that the table for the topic already exists in the database.

    The function connects to the database, constructs the appropriate SQL insert query
    based on the topic, and inserts the data point into the corresponding table.
    Commits the transaction and closes the connection.

    Parameters:
    topic (str): The topic name which corresponds to the table name in the database.
    timestamp (datetime): The timestamp of the data point.
    source_id (int): The ID of the data source (only applicable for renewable topics).
    value (float): The value of the data point.

    Raises:
    psycopg2.DatabaseError: If there is an error while interacting with the database.
    """

    conn = _connect()
    cursor = conn.cursor()
    print(f"Saving to {topic} table")
    table = topic.split("-")[0]
    print(f"Table: {table}")
    if table in RENEWABLES:
        query = f"INSERT INTO {table} (time, source_id, value) VALUES (%s, %s, %s)"
        cursor.execute(query, (timestamp, source_id, value))
    else:  # load and market have no source_id
        query = f"INSERT INTO {table} (time, value) VALUES (%s, %s)"
        cursor.execute(query, (timestamp, value))
    print(f"Data point saved to {table} table")
    conn.commit()

    cursor.close()
    conn.close()
    print("Connection closed")


def save_single_forecasts_to_db(source, source_id, forecasted_df):
    conn = _connect()
    cursor = conn.cursor()

    table_name = f"{source}_forecast"
    # Prepare insert query for renewables forecast
    if source in RENEWABLES:
        query = f"""
        INSERT INTO {table_name} (time, source_id, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s)
        """

        for time, row in forecasted_df.iterrows():
            cursor.execute(
                query,
                (
                    time,
                    source_id,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    row["value"],
                ),
            )

    else:
        query = f"""
        INSERT INTO {table_name} (time, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s)
        """

        for time, row in forecasted_df.iterrows():
            cursor.execute(
                query,
                (
                    time,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    row["value"],
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()


def save_forecasts_to_db(forecasted):
    """
    TODO: obsolete, use save_single_forecasts_to_db
    TODO: merge the two queries by adapting the DB structure and using 'None' for source_id in case of load and market

    Saves forecasted data from the provided dictionary to the database.
    The forecasted dictionary is expected to have the following structure:
        {
            "renewables": {
                renewable_type: {
                    source_id: DataFrame with columns ["yhat", "yhat_lower", "yhat_upper"] indexed by time
                },
                ...
            },
            "load": DataFrame with columns ["yhat", "yhat_lower", "yhat_upper"] indexed by time,
            "market": DataFrame with columns ["yhat", "yhat_lower", "yhat_upper"] indexed by time
        }

    Each DataFrame row is inserted into the corresponding forecast table in the database.
    """
    conn = _connect()
    cursor = conn.cursor()
    # Save forecasts for renewables
    renewables = forecasted.get("renewables", {})
    for renewable, sources in renewables.items():
        for source_id, df in sources.items():
            # Assuming forecast table naming convention: {renewable}_forecast
            table_name = f"{renewable}_forecast"
            # Prepare insert query for renewables forecast
            query = f"""
            INSERT INTO {table_name} (time, source_id, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s)
            """

            if "daily" not in df.columns:
                # TODO: handle this better
                df["daily"] = 0
                df["daily_lower"] = 0
                df["daily_upper"] = 0

            for time, row in df.iterrows():
                cursor.execute(
                    query,
                    (
                        row["ds"],
                        source_id,
                        row["trend"],
                        row["yhat_lower"],
                        row["yhat_upper"],
                        row["trend_lower"],
                        row["trend_upper"],
                        row["additive_terms"],
                        row["additive_terms_lower"],
                        row["additive_terms_upper"],
                        row["daily"],
                        row["daily_lower"],
                        row["daily_upper"],
                        row["multiplicative_terms"],
                        row["multiplicative_terms_lower"],
                        row["multiplicative_terms_upper"],
                        row["yhat"],
                    ),
                )

    for other in ["load", "market"]:

        df = forecasted[f"{other}"]
        table_name = f"{other}_forecast"

        query = f"""
        INSERT INTO {table_name} (time, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s, %s, %s)
        """

        if "daily" not in df.columns:
            # TODO: handle this better
            df["daily"] = 0
            df["daily_lower"] = 0
            df["daily_upper"] = 0

        for _, row in df.iterrows():
            cursor.execute(
                query,
                (
                    row["ds"],
                    row["trend"],
                    row["yhat_lower"],
                    row["yhat_upper"],
                    row["trend_lower"],
                    row["trend_upper"],
                    row["additive_terms"],
                    row["additive_terms_lower"],
                    row["additive_terms_upper"],
                    row["daily"],
                    row["daily_lower"],
                    row["daily_upper"],
                    row["multiplicative_terms"],
                    row["multiplicative_terms_lower"],
                    row["multiplicative_terms_upper"],
                    row["yhat"],
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()


def load_historical_data(
    type: str, source_id: str, start: str = None, end: str = None, top: int = None
):
    """
    Retrieves historical data for a specific type source and source_id (if applicable) within
    an optional time range [start, end].

    Parameters:
    ----------
    type : str
        Name of the table (e.g., 'solar', 'wind', 'load', 'market').
    source_id : str
        The source ID to filter on - IF APPLICABLE (renewables only).
    start : str, optional
        The start datetime string (inclusive). Format example: '2024-01-01 00:00:00+00'.
    end : str, optional
        The end datetime string (inclusive). Format example: '2024-01-02 23:59:59+00'.

    Returns:
    --------
    pd.DataFrame
        A DataFrame with columns ['time', 'value'], indexed by 'time'.
        If no data is found, returns an empty DataFrame.
    """
    conn = _connect()
    cursor = conn.cursor()

    # Build the WHERE clause dynamically based on whether start/end are provided
    params = []
    where_clauses = []

    if source_id is not None:
        where_clauses.append("source_id = %s")
        params.append(source_id)
    if start is not None:
        where_clauses.append("time >= %s")
        params.append(start)
    if end is not None:
        where_clauses.append("time <= %s")
        params.append(end)

    if params:
        # Combine the WHERE clauses
        where_clause = " AND ".join(where_clauses)
        query = f"""
            SELECT time, value
            FROM {type}
            WHERE {where_clause}
            ORDER BY time DESC
        """
        if top is not None:
            query += f" LIMIT {top}"
        cursor.execute(query, params)

    else:
        query = f"""
            SELECT time, value
            FROM {type}
            ORDER BY time DESC
        """
        if top is not None:
            query += f" LIMIT {top}"

        cursor.execute(query)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert to a DataFrame
    df = pd.DataFrame(rows, columns=["time", "value"])
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)

    return df


def load_forecasted_data(type: str, source_id: str, start: str = None, end: str = None):
    """
    TODO: remove redundancy by merging with load_historical_data (probably not feasible)
    TODO: select only what is needed
    Retrieves forecasted data for a specific type source and source_id (if applicable) within
    an optional time range [start, end].
    """
    conn = _connect()
    cursor = conn.cursor()

    # Build the WHERE clause dynamically based on whether start/end are provided
    params = []
    where_clauses = []
    if source_id is not None:
        where_clauses.append("source_id = %s")
        params.append(source_id)
    if start is not None:
        where_clauses.append("time >= %s")
        params.append(start)
    if end is not None:
        where_clauses.append("time <= %s")
        params.append(end)

    if params:
        # Combine the WHERE clauses
        where_clause = " AND ".join(where_clauses)
        query = f"""
            SELECT time, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat
            FROM {type+'_forecast'}
            WHERE {where_clause}
            ORDER BY time
        """
        cursor.execute(query, params)

    else:
        query = f"""
            SELECT time, trend, yhat_lower, yhat_upper, trend_lower, trend_upper, additive_terms,additive_terms_lower, additive_terms_upper, daily, daily_lower, daily_upper, multiplicative_terms, multiplicative_terms_lower, multiplicative_terms_upper, yhat
            FROM {type+'_forecast'}
            ORDER BY time
        """
        cursor.execute(query)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Convert to a DataFrame
    df = pd.DataFrame(
        rows,
        columns=[
            "time",
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
        ],
    )
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)

    return df


def query_source_ids(source: str):
    """
    Query the database to retrieve available source IDs for the given source type.

    Parameters:
    ----------
    source : str
        The source type (e.g., 'solar', 'wind').

    Returns:
    --------
    List[str]
        A list of source IDs for the given source type.
    """
    conn = _connect()
    cursor = conn.cursor()

    query = f"SELECT DISTINCT source_id FROM {source};"
    cursor.execute(query)

    rows = cursor.fetchall()
    source_ids = [row[0] for row in rows]

    cursor.close()
    conn.close()

    return source_ids


# def dump_csv_folder_to_db(folder_path: str):
#     """
#     Loops over all .csv files in `folder_path`, each named "<source_id>_<source>.csv".
#     Each CSV has exactly one column of values (no time column).

#     For each file:
#       1. Parse filename to extract `source_id` and `source`.
#       2. Read the single column of data.
#       3. Generate a simple sequence of timestamps (e.g. consecutive minutes) for each row.
#       4. Insert each row into the DB using `save_to_db(...)`.

#     Parameters
#     ----------
#     folder_path : str
#         Path to the folder containing CSV files.
#     """

#     for filename in os.listdir(folder_path):
#         if not filename.endswith(".csv"):
#             continue  # skip non-CSV files

#         full_path = os.path.join(folder_path, filename)

#         # 1. Parse out source_id & source
#         #    Example filename: "0GFA4K_solar.csv"
#         name_no_ext = filename.rsplit(".", 1)[0]  # -> "0GFA4K_solar"
#         parts = name_no_ext.split("_", 1)  # -> ["0GFA4K", "solar"]
#         if len(parts) != 2:
#             print(f"Skipping {filename}: not in 'sourceid_source.csv' format.")
#             continue
#         source_id, source = parts

#         # 2. Read CSV with one single column
#         df = pd.read_csv(full_path, index_col=0)

#         # Insert row by row into DB
#         for i, row in df.iterrows():
#             ts = i
#             # assume only one columns
#             val = str(row.values[0])
#             if source in RENEWABLES:
#                 # for solar / wind, pass the parsed source_id
#                 save_to_db(source, ts, source_id, val)
#             else:
#                 # for load / market, pass None or ignore `source_id`
#                 save_to_db(source, ts, None, val)

#         print(f"Inserted {len(df)} rows from file '{filename}' into table '{source}'.")


def dump_csv_folder_to_db_and_start_streaming(folder_path: str):
    """
    Loops over all .csv files in `folder_path`, each named "<source_id>_<source>.csv".
    We assume:
      - The CSV index is the "time" column (or at least a date/datetime)
      - There is exactly one data column named 'value' (or 1 unnamed column we rename).
    Then we insert them in bulk using execute_values for faster loading.
    """

    for filename in os.listdir(folder_path):
        if "weather" in filename:
            continue
        if not filename.endswith(".csv"):
            continue

        full_path = os.path.join(folder_path, filename)

        # 1. Parse out source_id & source from the filename
        name_no_ext = filename.rsplit(".", 1)[0]  # -> "0GFA4K_solar"
        source_id = name_no_ext.split("_")[0]  # ->  "0GFA4K"
        source = name_no_ext.split("_")[1]  # -> "solar"

        # 2. Load CSV into DataFrame
        #    We expect a single column 'value' or no header -> rename to 'value'.
        #    The index is your timestamp.
        df = pd.read_csv(full_path, index_col=0)

        # first 10% of the data will be stored in the database
        df_to_store = df.iloc[: int(len(df) * 0.1)]
        df_to_stream = df.iloc[int(len(df) * 0.1) :]

        # 3. Decide table name and source_id usage
        #    - If 'source' is in RENEWABLES, we use that as the table name, else it might be "load" or "market"
        table_name = source  # e.g. "solar", "wind", "load", "market"

        # For each row, we need (time, source_id, value) for renewables or (time, value) for non-renewables
        # but let's unify as (time, source_id, value) and set source_id=None if not renewables.

        # We'll build a list of tuples
        data_tuples = []
        for i, row in df_to_store.iterrows():
            t = i
            val = float(row.values[0]) if pd.notnull(row.values[0]) else None

            # If source is renewable, use the parsed source_id; otherwise None
            sid = source_id if source in RENEWABLES else None

            # We'll store them in the order that matches our final INSERT statement
            data_tuples.append((t, sid, val))

        # 4. Bulk insert with execute_values
        #    Build the correct SQL depending on whether table_name is renewable or not
        #    But let's unify: the table always has columns (time, source_id, value) for solar/wind,
        #    while load/market have columns (time, value). We'll just pass source_id as NULL for load/market.

        if source in RENEWABLES:
            insert_sql = f"""
                INSERT INTO {table_name} (time, source_id, value)
                VALUES %s
            """
            with _connect() as conn, conn.cursor() as cursor:
                execute_values(cursor, insert_sql, data_tuples)
        else:
            insert_sql = f"""
                INSERT INTO {table_name} (time, value)
                VALUES %s
            """
            with _connect() as conn, conn.cursor() as cursor:
                data_tuples = [(t, val) for t, _, val in data_tuples]
                execute_values(cursor, insert_sql, data_tuples)

        print(
            f"Inserted {len(data_tuples)} rows from '{filename}' into table '{table_name}'."
        )

        new_producer_bundle = (source, source_id, df_to_stream)
        new_producer_process = Process(
            target=kafka_produce, args=(new_producer_bundle, 60)
        )
        new_producer_process.start()
