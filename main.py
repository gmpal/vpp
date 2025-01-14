from generation import (
    generate_weather_data,
    generate_wind_data,
    generate_pv_data,
    generate_synthetic_load_data,
)

from communication import (
    kafka_consume,
    kafka_produce,
    kafka_consume_and_store,
)

from multiprocessing import Process

if __name__ == "__main__":

    starting_date = "2025-01-07 00:00"
    num_days = 31
    output_path = "./data/"

    # Generate weather data
    weather_data = generate_weather_data(
        starting_date, num_days=num_days, output_path=output_path
    )
    load_data = generate_synthetic_load_data(
        starting_date, num_days=num_days, output_path=output_path
    )

    # Generate wind power output data
    wind_power_output = generate_wind_data(
        weather_data=weather_data, output_path=output_path
    )
    solar_power_output = generate_pv_data(
        weather_data=weather_data, output_path=output_path
    )

    p = Process(target=kafka_produce, args=(output_path,))
    p.start()

    p = Process(target=kafka_consume_and_store)
    p.start()
