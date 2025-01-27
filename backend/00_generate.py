from src.generation import (
    generate_weather_data,
    generate_wind_data,
    generate_pv_data,
    generate_synthetic_load_data,
    generate_synthetic_market_price,
    read_generation_config,
)

from src.sources import create_new_source

from src.communication import (
    make_producers_info,
    kafka_produce,
    kafka_consume_centralized,
)

import src.db as db

from multiprocessing import Process
import os
import random
import datetime

if __name__ == "__main__":

    configs = read_generation_config()

    output_path = configs["output_path"]
    num_sources = configs["num_sources"]
    freq = configs["freq"]
    num_days = configs["num_days"]
    sleeping_time = configs["sleeping_time"]
    starting_date = configs["starting_date"]

    # emtpy folder output_path
    for file in os.listdir(output_path):
        os.remove(output_path + file)

    for _ in range(num_sources):
        create_new_source("wind")
        create_new_source("solar")

    generate_synthetic_load_data(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        freq=freq,
    )

    generate_synthetic_market_price(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        freq=freq,
    )

    # processes = []
    # for producer_bundle in producers_bundles:
    #     producer_process = Process(
    #         target=kafka_produce, args=(producer_bundle, sleeping_time)
    #     )
    #     processes.append(producer_process)

    # db.reset_tables()

    # consumer_process = Process(target=kafka_consume_centralized)
    # processes.append(consumer_process)

    # # Start all processes
    # for process in processes:
    #     process.start()
    # # Wait for all processes to complete
    # for producer_process in processes:
    #     producer_process.join()

    # # forecast_and_save()
