from backend.src.db import dump_csv_folder_to_db_and_start_streaming, reset_tables


if __name__ == "__main__":
    reset_tables()
    dump_csv_folder_to_db_and_start_streaming("data")
