import pandas as pd
import numpy as np
from windpowerlib import ModelChain, WindTurbine
from windpowerlib import create_power_curve
import pvlib
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain as PVModelChain
from pvlib.location import Location

import configparser
from datetime import datetime

# TODO: change saving folder structure


def read_generation_config(filename: str = "config.ini") -> dict:
    config = configparser.ConfigParser()
    config.read(filename)
    config = {
        "output_path": config.get("Generation", "output_path"),
        "num_sources": int(config.get("Generation", "num_sources")),
        "freq": config.get("Generation", "freq"),
        "num_days": int(config.get("Generation", "num_days")),
        "sleeping_time": int(config.get("Generation", "sleeping_time")),
        "starting_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return config


def generate_weather_data(
    starting_date: str = "2025-01-07 00:00",
    num_days: int = 7,
    freq: str = "h",
    output_path: str = "../data/",
    source_id: str = 1,
) -> pd.DataFrame:
    """
    Generate synthetic weather data for a specified number of days starting from a given date.
    Parameters:
    starting_date (str): The starting date and time for the weather data in the format "YYYY-MM-DD HH:MM".
    num_days (int): The number of days for which to generate weather data.
    freq (str): The frequency of the data points (e.g., 'h' for hourly).
    output_path (str): The file path to save the generated weather data as a CSV file. If None, the data will not be saved.
    source_id (str): The unique identifier for the weather data source.
    Returns:
    pd.DataFrame: A DataFrame containing the generated weather data with the following columns:
        - 'ghi': Global Horizontal Irradiance (W/m²)
        - 'dni': Direct Normal Irradiance (W/m²)
        - 'dhi': Diffuse Horizontal Irradiance (W/m²)
        - ('wind_speed', 100): Wind speed at 100m height (m/s)
        - ('temperature', 2): Temperature at 2m above ground level (°C)
        - ('pressure', 0): Atmospheric pressure at sea level (Pa)
    """

    # Set random seed for reproducibility
    # get an integer from  source_id
    seed = int("".join([c for c in source_id if c.isdigit()]))
    np.random.seed(seed)

    # Set the time index for one day (24 hourly intervals)
    time_index = pd.date_range(starting_date, periods=24 * num_days, freq=freq)

    # Define base patterns for synthetic weather data

    # Solar radiation (GHI) follows a sine wave pattern for daylight hours (sunrise to sunset)
    solar_radiation = np.maximum(
        0, np.sin(np.linspace(-np.pi / 2, np.pi / 2, len(time_index))) * 1000
    )

    # Wind speed follows a cosine wave pattern, typically stronger at night
    wind_speed_pattern = np.clip(
        np.cos(np.linspace(0, 2 * np.pi, len(time_index))) * 6 + 6, 3, 12
    )

    # Temperature follows a sine wave pattern, with colder temperatures at night
    temperature_pattern = np.clip(
        5 + np.sin(np.linspace(-np.pi / 2, np.pi / 2, len(time_index))) * 10, -5, 15
    )

    # Add random noise to introduce variability for realism
    solar_radiation += np.random.normal(
        0, 50, len(time_index)
    )  # Noise for solar radiation
    wind_speed_pattern += np.random.normal(
        0, 1, len(time_index)
    )  # Noise for wind speed
    temperature_pattern += np.random.normal(
        0, 1, len(time_index)
    )  # Noise for temperature

    # Create the weather DataFrame with all variables
    weather_data = pd.DataFrame(
        {
            # Solar data: GHI (Global Horizontal Irradiance), DNI (Direct Normal Irradiance), DHI (Diffuse Horizontal Irradiance)
            "ghi": np.clip(
                solar_radiation, 0, 1000
            ),  # Clip values to realistic range (0–1000 W/m²)
            "dni": np.clip(solar_radiation * 0.8, 0, 800),  # DNI as 80% of GHI
            "dhi": np.clip(solar_radiation * 0.2, 0, 200),  # DHI as 20% of GHI
            # Wind speed at hub height (100m)
            ("wind_speed", 100): np.clip(
                wind_speed_pattern, 3, 12
            ),  # Clip values to 3–12 m/s
            # Temperature at 2m above ground level
            ("temperature", 2): np.clip(
                temperature_pattern, -10, 15
            ),  # Clip values to -10°C to 15°C
            # Atmospheric pressure at sea level
            ("pressure", 0): 101325
            + np.random.normal(
                0, 500, len(time_index)
            ),  # Add noise to baseline pressure (Pa)
        },
        index=time_index,
    )

    # Ensure columns with MultiIndex for variables with height (required for windpowerlib)
    weather_data.columns = pd.MultiIndex.from_tuples(
        [(col if isinstance(col, tuple) else (col, "")) for col in weather_data.columns]
    )

    if output_path:
        weather_data.to_csv(output_path + f"{source_id}_weather_data.csv")

    return weather_data


def generate_wind_data(
    weather_data_path: str = None,
    weather_data: pd.DataFrame = None,
    output_path: str = "../data/",
    plot: bool = False,
    source_id: str = 1,
) -> pd.DataFrame:
    """
    Simulates wind turbine power output based on weather data and a predefined power curve.
    Parameters:
    weather_data_path (str): Path to the CSV file containing weather data with columns 'wind_speed', 'temperature', and 'pressure'.
    output_path (str, optional): Path to save the simulated power output CSV file. Defaults to "../data/wind_turbine_power_output.csv".
    plot (bool, optional): If True, plots the simulated power output. Defaults to False.
    Returns:
    pd.DataFrame: DataFrame containing the simulated power output in kW.
    """

    # Define power curve as a DataFrame
    power_curve = pd.DataFrame(
        {
            "wind_speed": [
                0,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                25,
            ],  # Wind speeds (m/s)
            "value": [
                0.0,
                0.0,
                0.010,
                0.050,
                0.100,
                0.300,
                0.700,
                1.200,
                2.000,
                2.500,
                3.000,
                3.050,
                3.050,
                3.050,
                3.050,
                3.050,
                2.500,
                0.0,
            ],  # Power output (kW)
        }
    )

    # Wind turbine specifications
    turbine_specifications = {
        "turbine_type": "custom_turbine",
        "hub_height": 100,  # Hub height in meters
        "power_curve": power_curve,  # Directly pass the DataFrame
    }

    # Create the WindTurbine object
    turbine = WindTurbine(**turbine_specifications)

    if weather_data is None:
        if weather_data_path is None:
            raise ValueError(
                "Either weather_data_path or weather_data must be provided."
            )
        # 2. Define weather data
        weather_data = pd.read_csv(
            weather_data_path, index_col=0, parse_dates=True, header=[0, 1]
        )

    weather_data = weather_data[["wind_speed", "temperature", "pressure"]]

    # 3. Simulate wind power generation
    modelchain = ModelChain(turbine)
    modelchain.run_model(weather_data)

    power_output = modelchain.power_output  # Power output in kW

    if output_path:
        power_output.to_csv(output_path + f"{source_id}_wind.csv")

    if plot:
        power_output.plot(
            title="Simulated Wind Turbine Power Output",
            xlabel="Time",
            ylabel="Power (kW)",
        )

    return power_output


def generate_pv_data(
    weather_data_path: str = None,
    weather_data: pd.DataFrame = None,
    output_path: str = "../data/",
    plot: bool = False,
    source_id: str = 1,
) -> pd.DataFrame:
    """
    Generate photovoltaic (PV) data based on weather data and simulate solar power generation.
    Parameters:
    weather_data_path (str, optional): Path to the CSV file containing weather data. Default is None.
    weather_data (pd.DataFrame, optional): DataFrame containing weather data. Default is None.
    output_path (str, optional): Path to save the generated solar panel power output CSV file. Default is "../data/solar_panel_generation.csv".
    plot (bool, optional): Whether to plot the simulated solar panel power output. Default is False.
    Returns:
    pd.DataFrame: DataFrame containing the simulated AC power output of the solar panels.
    Raises:
    ValueError: If neither weather_data nor weather_data_path is provided.
    """

    # 1. Define the site location
    latitude = 48.2
    longitude = 16.37
    tz = "Europe/Vienna"

    site = Location(latitude, longitude, tz=tz)

    # 2. Define the solar panel characteristics
    module_parameters = {
        "pdc0": 250,  # Power output at Standard Test Conditions (W)
        "gamma_pdc": -0.0045,  # Temperature coefficient (1/°C)
    }

    inverter_parameters = {
        "pdc0": 240,  # Inverter max DC power (W)
        "eta_inv_nom": 0.96,  # Nominal inverter efficiency
    }

    # 3. Define the system configuration
    system = PVSystem(
        surface_tilt=30,  # Panel tilt angle (degrees)
        surface_azimuth=180,  # Panel azimuth angle (degrees, 180 = south)
        module_parameters=module_parameters,
        inverter_parameters=inverter_parameters,
        racking_model="open_rack",
        module_type="glass_glass",
    )

    if weather_data is None:
        if weather_data_path is None:
            raise ValueError(
                "You need to provide either weather_data or weather_data_path"
            )
        weather = pd.read_csv(
            weather_data_path, index_col=0, parse_dates=True, header=0
        )
    # Drop second level of header
    weather_data.columns = weather_data.columns.droplevel(1)

    weather = weather_data.iloc[
        1:, :-1
    ]  # drop the second header and the last column (pressure)
    # rename temperature to temp_air
    weather.rename(columns={"temperature": "temp_air"}, inplace=True)
    # sort the columns
    weather = weather[["ghi", "dni", "dhi", "temp_air", "wind_speed"]]

    # 5. Simulate the solar power generation
    mc = PVModelChain(system, site, aoi_model="physical", spectral_model="no_loss")
    mc.run_model(weather)

    # Output the AC power (energy generation)
    ac_power = mc.results.ac

    if output_path:
        ac_power.to_csv(output_path + f"{source_id}_solar.csv", header=True)

    # Plot the results
    if plot:
        ac_power.plot(
            title="Simulated Solar Panel Power Output",
            xlabel="Time",
            ylabel="Power (W)",
        )


def generate_synthetic_load_data(
    starting_date: str = "2025-01-07 00:00",
    num_days: int = 7,
    freq: str = "h",
    output_path: str = "../data/",
) -> pd.DataFrame:
    """
    Generate synthetic load data for a specified number of days.
    Parameters:
    starting_date (str): The starting date and time for the data generation in the format "YYYY-MM-DD HH:MM".
    num_days (int): The number of days for which to generate the load data.
    freq (str): The frequency of the data points (e.g., 'h' for hourly).
    output_path (str): The file path where the generated data will be saved as a CSV file. If None, the data will not be saved.
    Returns:
    pd.DataFrame: A DataFrame containing the generated load data with a datetime index.
    """
    hours = 24 * num_days
    # Create an hourly date range
    time_index = pd.date_range(start=starting_date, freq=freq, periods=hours)

    # Base array of zeros
    load_kW = np.zeros(hours)

    for i in range(hours):
        hour_of_day = time_index[i].hour

        if 0 <= hour_of_day < 6:
            # Nighttime: relatively low load
            load_kW[i] = 0.4 * 10 + 0.2 * np.random.rand()  # ~0.4 kW ± noise
        elif 6 <= hour_of_day < 17:
            # Daytime: moderate load
            load_kW[i] = 0.8 * 10 + 0.3 * np.random.rand()  # ~0.8 kW ± noise
        else:
            # Evening peak: higher load
            load_kW[i] = 1.5 * 10 + 0.5 * np.random.rand()  # ~1.5 kW ± noise

    # Create a pandas Series
    load_series = pd.Series(load_kW, index=time_index, name="Load_kW")

    if output_path:
        load_series.to_csv(output_path + "synthetic_load_data.csv", header=True)
    return load_series


def generate_synthetic_market_price(
    starting_date: str = "2025-01-07 00:00",
    num_days: int = 7,
    freq: str = "h",
    output_path: str = "../data/",
) -> pd.Series:
    """
    Generate synthetic market price data for a specified number of days.

    Parameters:
    starting_date (str): The starting date and time for the data generation in the format "YYYY-MM-DD HH:MM".
    num_days (int): The number of days for which to generate the market price data.
    freq (str): The frequency of the data points (e.g., 'h' for hourly).
    output_path (str): The file path where the generated data will be saved as a CSV file.
                       If empty or None, the data will not be saved.

    Returns:
    pd.Series: A Series containing the generated market price data with a datetime index.
    """
    hours = 24 * num_days
    # Create an hourly date range
    time_index = pd.date_range(start=starting_date, freq=freq, periods=hours)

    # Initialize an array to hold market price values
    prices = np.zeros(hours)

    # Base price and variability parameters
    base_price = 50  # $/MWh base
    amplitude = 20  # amplitude for sinusoidal fluctuation
    noise_level = 5  # noise level in price

    for i in range(hours):
        hour_of_day = time_index[i].hour

        # Use a sinusoidal pattern to simulate diurnal price variations
        # Higher prices during peak hours (assumed 17:00-21:00) and lower during off-peak.
        # Additionally add some random noise.
        # Normalize hour_of_day to range [0, 2π] for one full cycle
        angle = (hour_of_day / 24) * 2 * np.pi
        diurnal_variation = amplitude * np.sin(angle)

        # Adjust base price with diurnal variation and noise
        prices[i] = base_price + diurnal_variation + noise_level * np.random.randn()

    # Create a pandas Series
    price_series = pd.Series(prices, index=time_index, name="MarketPrice")

    if output_path:
        price_series.to_csv(output_path + "synthetic_market_price.csv", header=True)
    return price_series
