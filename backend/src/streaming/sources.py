import random
import string
from multiprocessing import Process

from backend.src.pipelines.generation import (
    generate_pv_data,
    generate_weather_data,
    generate_wind_data,
    read_generation_config,
)
from backend.src.streaming.communication import (
    kafka_produce,
    make_single_producer_info,
)


def create_new_source(source_type: str, kakfa_flag=False, latitude=None, longitude=None):
    """
    Creates a new data source for weather forecasting and starts a Kafka producer process.
    Args:
        source_type (str): The type of the source to create. Only "solar" is supported.
        kakfa_flag (bool): Whether to start a Kafka producer.
        latitude (float): Latitude of the source location.
        longitude (float): Longitude of the source location.
    Returns:
        Process: The Kafka producer process that was started for the new source.
    Raises:
        ValueError: If the source_type is not "solar".
    This function performs the following steps:
        1. Reads the generation configuration.
        2. Generates weather data for the new source.
        3. Generates PV data for the source.
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

    # random sequence of nums and letters
    source_id = "".join(random.choices(string.digits, k=6))

    print(f"Creating new source with ID: {source_id} at ({latitude}, {longitude})")
    # Generate weather data for the new source
    weather_data = generate_weather_data(
        starting_date,
        num_days=num_days,
        output_path=output_path,
        source_id=source_id,
        freq=freq,
        latitude=latitude,
        longitude=longitude,
    )

    if source_type == "solar":
        generate_pv_data(
            weather_data=weather_data,
            output_path=output_path,
            source_id=source_id,
            latitude=latitude,
            longitude=longitude,
        )
    elif source_type == "wind":
        generate_wind_data(
            weather_data=weather_data,
            output_path=output_path,
            source_id=source_id,
            latitude=latitude,
            longitude=longitude,
        )
    else:
        raise ValueError(f"Unsupported source_type: {source_type}. Must be 'solar' or 'wind'.")

    if kakfa_flag:
        # Update producers_bundles to include the new source
        new_producer_bundle = make_single_producer_info(output_path, source_type, source_id)

        # Start a new Kafka producer process for the new source
        new_producer_process = Process(target=kafka_produce, args=(new_producer_bundle, sleeping_time))
        new_producer_process.start()

        return new_producer_process, source_id

    return None, source_id
