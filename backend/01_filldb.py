from src.db import dump_csv_folder_to_db, reset_tables


if __name__ == "__main__":
    reset_tables()
    dump_csv_folder_to_db("data")
