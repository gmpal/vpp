from src.generation import (
    generate_weather_data,
    generate_wind_data,
    generate_pv_data,
    generate_synthetic_load_data,
    generate_synthetic_market_price,
)

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

    # now
    starting_date = datetime.datetime.now()
    output_path = "./data/"
    num_sources = 2
    freq = "s"
    num_days = 100  # doesnt matter because minutes * 24
    sleeping_time = 1

    # emtpy folder output_path
    for file in os.listdir(output_path):
        os.remove(output_path + file)

    for source_id in range(1, num_sources + 1):
        # Generate weather data
        weather_data = generate_weather_data(
            starting_date,
            num_days=num_days,
            output_path=output_path,
            source_id=source_id,
            freq=freq,
        )

        # random boolean selector
        if random.randint(0, 1):
            # Generate wind power output data
            generate_wind_data(
                weather_data=weather_data,
                output_path=output_path,
                source_id=source_id,
            )
        else:
            generate_pv_data(
                weather_data=weather_data,
                output_path=output_path,
                source_id=source_id,
            )

    load_data = generate_synthetic_load_data(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        freq=freq,
    )

    market_prices = generate_synthetic_market_price(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        freq=freq,
    )

    producers_bundles = make_producers_info(output_path)

    processes = []
    for producer_bundle in producers_bundles:
        producer_process = Process(
            target=kafka_produce, args=(producer_bundle, sleeping_time)
        )
        processes.append(producer_process)

    db.reset_tables()

    consumer_process = Process(target=kafka_consume_centralized)
    processes.append(consumer_process)

    # Start all processes
    for process in processes:
        process.start()
    # Wait for all processes to complete
    for producer_process in processes:
        producer_process.join()

    # forecast_and_save()
