import os
import pandas as pd
from backend.src.db import DatabaseManager, CrudManager, SchemaManager
from backend.src.streaming.communication import kafka_produce
from multiprocessing import Process

db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)
schema_manager = SchemaManager(db_manager)


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
            sid = source_id if source in db_manager.renewables else None

            # We'll store them in the order that matches our final INSERT statement
            data_tuples.append((t, sid, val))

        # 4. Bulk insert with execute_values
        #    Build the correct SQL depending on whether table_name is renewable or not
        #    But let's unify: the table always has columns (time, source_id, value) for solar/wind,
        #    while load/market have columns (time, value). We'll just pass source_id as NULL for load/market.

        if source in db_manager.renewables:
            query = f"""
                INSERT INTO {table_name} (time, source_id, value)
                VALUES (%s, %s, %s)
            """
        else:
            query = f"""
                INSERT INTO {table_name} (time, value)
                VALUES (%s, %s)
            """
            data_tuples = [(t, val) for t, _, val in data_tuples]

        for t in data_tuples:
            db_manager.execute(query, t)

        print(
            f"Inserted {len(data_tuples)} rows from '{filename}' into table '{table_name}'."
        )

        new_producer_bundle = (source, source_id, df_to_stream)
        new_producer_process = Process(
            target=kafka_produce, args=(new_producer_bundle, 60)
        )
        new_producer_process.start()


if __name__ == "__main__":
    schema_manager.reset_all_tables()
    dump_csv_folder_to_db_and_start_streaming("./backend/data/")
