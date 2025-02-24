from multiprocessing import Process

from backend.src.pipelines.generation import (
    generate_weather_data,
    generate_wind_data,
    generate_pv_data,
    read_generation_config,
)

from backend.src.streaming.communication import (
    make_single_producer_info,
    kafka_produce,
)

import random
import string


def create_new_source(source_type: str, kakfa_flag=False):
    """
    Creates a new data source for weather forecasting and starts a Kafka producer process.
    Args:
        source_type (str): The type of the source to create, either "wind" or "pv".
    Returns:
        Process: The Kafka producer process that was started for the new source.
    Raises:
        ValueError: If the source_type is not "wind" or "pv".
    This function performs the following steps:
        1. Reads the generation configuration.
        2. Generates weather data for the new source.
        3. Depending on the source_type, generates either wind or PV data.
        4. Updates the producers_bundles to include the new source.
        5. Starts a new Kafka producer process for the new source.
    """

    configs = read_generation_config()
    # configs is a dict
    output_path = configs["output_path"]
    starting_date = configs["starting_date"]
    num_days = configs["num_days"]
    freq = configs["freq"]
    sleeping_time = configs["sleeping_time"]

    # random sequence of nums nad letters
    source_id = "".join(random.choices(string.digits, k=6))

    print(f"Creating new source with ID: {source_id}")
    # Generate weather data for the new source
    weather_data = generate_weather_data(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        source_id=source_id,
        freq=freq,
    )

    # Decide randomly whether to generate wind or PV data
    if source_type == "wind":
        generate_wind_data(
            weather_data=weather_data,
            output_path=output_path,
            source_id=source_id,
        )
    elif source_type == "solar":
        generate_pv_data(
            weather_data=weather_data,
            output_path=output_path,
            source_id=source_id,
        )

    if kakfa_flag:
        # Update producers_bundles to include the new source
        new_producer_bundle = make_single_producer_info(
            output_path, source_type, source_id
        )

        # Start a new Kafka producer process for the new source
        new_producer_process = Process(
            target=kafka_produce, args=(new_producer_bundle, sleeping_time)
        )
        new_producer_process.start()

        return new_producer_process, source_id

    return None, source_id
