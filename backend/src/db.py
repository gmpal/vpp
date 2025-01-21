import configparser
import psycopg2
import pandas as pd

RENEWABLES = ["solar", "wind"]  # scalable for more renewables


def _connect():
    # ------------------------------
    # 1. Read database config
    # ------------------------------
    config = configparser.ConfigParser()
    config.read("config.ini")

    db_connection_info = {
        "dbname": config["TimescaleDB"]["dbname"],
        "user": config["TimescaleDB"]["user"],
        "password": config["TimescaleDB"]["password"],
        "host": config["TimescaleDB"]["host"],
        "port": config["TimescaleDB"]["port"],
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

    table = topic.split("-")[0]

    if table in RENEWABLES:
        query = f"INSERT INTO {table} (time, source_id, value) VALUES (%s, %s, %s)"
        cursor.execute(query, (timestamp, source_id, value))
    else:  # load and market have no source_id
        query = f"INSERT INTO {table} (time, value) VALUES (%s, %s)"
        cursor.execute(query, (timestamp, value))

    conn.commit()
    print(f"Inserted data from {topic} at {timestamp}")

    cursor.close()
    conn.close()


def save_forecasts_to_db(forecasted):
    """
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

    # Save forecast for load
    if "load" in forecasted:
        df = forecasted["load"]
        table_name = "load_forecast"
    elif "market" in forecasted:
        df = forecasted["market"]
        table_name = "market_forecast"

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


def load_historical_data(type: str, source_id: str, start: str = None, end: str = None):
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
            ORDER BY time
        """
        cursor.execute(query, params)

    else:
        query = f"""
            SELECT time, value
            FROM {type}
            ORDER BY time
        """
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
