# app.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import pandas as pd
import asyncpg
import os

from src.db import (
    load_from_db,
    load_historical_data,
    query_source_ids,
    load_forecasted_data,
    save_battery_state,
)
from src.battery import Battery  # Adjust import as necessary
from src.sources import create_new_source
from src.optimization import optimize


RENEWABLES = ["solar", "wind"]  # scalable for more renewables
COUNTER = 0

app = FastAPI()

# Configure CORS if your frontend is on a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RealTimeDataPoint(BaseModel):
    timestamp: str
    value: float
    # TODO: consider merging with HistoricalDataPoint if they share the same structure


class HistoricalDataPoint(BaseModel):
    timestamp: str
    value: float


class ForecastedDataPoint(BaseModel):
    timestamp: str
    trend: float
    yhat_lower: float
    yhat_upper: float
    trend_lower: float
    trend_upper: float
    additive_terms: float
    additive_terms_lower: float
    additive_terms_upper: float
    daily: float
    daily_lower: float
    daily_upper: float
    multiplicative_terms: float
    multiplicative_terms_lower: float
    multiplicative_terms_upper: float
    yhat: float


class DeviceCounts(BaseModel):
    solar: int
    wind: int
    # TODO: Add other types if needed
    # How to make this scalable?


class Source(BaseModel):
    source_type: str
    source_id: str


# In-memory store for batteries
batteries: Dict[str, Battery] = {}


# Pydantic models for battery responses and operations
class BatteryStatus(BaseModel):
    battery_id: str
    capacity_kWh: float
    soc_kWh: float
    max_charge_kW: float
    max_discharge_kW: float
    eta: float


class BatteryOperation(BaseModel):
    power_kW: float
    duration_h: float = 1.0  # default duration


class BatteryAddRequest(BaseModel):
    capacity_kWh: float
    current_soc_kWh: float
    max_charge_kW: float
    max_discharge_kW: float
    eta: float


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/batteries", response_model=List[BatteryStatus])
def get_all_batteries():
    """
    Returns list and current state of all batteries.
    """
    response = []
    for battery_id, battery in batteries.items():
        response.append(
            BatteryStatus(
                battery_id=battery_id,
                capacity_kWh=battery.capacity_kWh,
                soc_kWh=battery.current_soc_kWh,
                max_charge_kW=battery.max_charge_kW,
                max_discharge_kW=battery.max_discharge_kW,
                eta=battery.round_trip_efficiency,
            )
        )
    return response


@app.post("/api/batteries", response_model=BatteryStatus)
def add_battery(battery: BatteryAddRequest):
    """
    Adds a new battery.
    """
    # Generate a unique battery ID
    battery_id = f"battery_{len(batteries) + 1}"
    capacity_kWh = battery.capacity_kWh
    current_soc_kWh = battery.current_soc_kWh
    max_charge_kW = battery.max_charge_kW
    max_discharge_kW = battery.max_discharge_kW
    eta = battery.eta

    # Create a new Battery instance
    new_battery = Battery(
        battery_id=battery_id,
        capacity_kWh=capacity_kWh,
        current_soc_kWh=current_soc_kWh,
        max_charge_kW=max_charge_kW,
        max_discharge_kW=max_discharge_kW,
        round_trip_efficiency=eta,
    )

    # Store in the in-memory dictionary
    batteries[battery_id] = new_battery

    # TODO: decide if we want to save the battery state to the database
    # save_battery_state(new_battery)

    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=new_battery.capacity_kWh,
        soc_kWh=new_battery.current_soc_kWh,
        max_charge_kW=new_battery.max_charge_kW,
        max_discharge_kW=new_battery.max_discharge_kW,
        eta=new_battery.round_trip_efficiency,
    )


@app.delete("/api/batteries/{battery_id}", response_model=None)
def remove_battery(battery_id: str):
    """
    Removes a battery from the in-memory store.
    """
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")

    del batteries[battery_id]

    # TODO: decide if we want to remove the battery state from the database
    # remove_battery_state(battery_id)

    return {"detail": "Battery removed successfully"}


@app.post("/api/batteries/{battery_id}/charge", response_model=BatteryStatus)
def charge_battery(battery_id: str, operation: BatteryOperation):
    """
    Triggers a charge operation on a specific battery, updating its state.
    """
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")

    battery = batteries[battery_id]
    battery.charge(power_kW=operation.power_kW, duration_h=operation.duration_h)

    # TODO: decide if we want to save the battery state to the database
    # save_battery_state(battery)

    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=battery.capacity_kWh,
        soc_kWh=battery.current_soc_kWh,
        max_charge_kW=battery.max_charge_kW,
        max_discharge_kW=battery.max_discharge_kW,
        eta=battery.round_trip_efficiency,
    )


@app.post("/api/batteries/{battery_id}/discharge", response_model=BatteryStatus)
def discharge_battery(battery_id: str, operation: BatteryOperation):
    """
    Triggers a discharge operation on a specific battery, updating its state.
    """
    if battery_id not in batteries:
        raise HTTPException(status_code=404, detail="Battery not found")

    battery = batteries[battery_id]
    battery.discharge(power_kW=operation.power_kW, duration_h=operation.duration_h)

    # TODO: decide if we want to save the battery state to the database
    # save_battery_state(battery)

    return BatteryStatus(
        battery_id=battery_id,
        capacity_kWh=battery.capacity_kWh,
        soc_kWh=battery.current_soc_kWh,
        max_charge_kW=battery.max_charge_kW,
        max_discharge_kW=battery.max_discharge_kW,
        eta=battery.round_trip_efficiency,
    )


@app.get("/api/add-source")
def add_new_source(source_type: str):
    """
    Endpoint to add a new renewable source. It triggers CSV generation and starts a Kafka producer.
    """
    try:
        # Call the creation logic
        _, source_id = create_new_source(source_type=source_type, kakfa_flag=True)

        return Source(source_type=source_type, source_id=source_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/realtime-data/{source}", response_model=List[RealTimeDataPoint])
def query_real_time_data(
    source: str, source_id: str = None, since: Optional[str] = None
):
    """
    Fetches real-time data for a given source and optional source_id since a specified time.
    Args:
        source (str): The source from which to fetch real-time data.
        source_id (str, optional): The identifier for the specific source. Defaults to None.
        since (str, optional): The starting point in time (ISO 8601 format) from which to fetch data. Defaults to None.
    Returns:
        List[RealTimeDataPoint]: A list of RealTimeDataPoint objects containing the timestamp and value of the data points.
    """

    # Parse the 'since' parameter if provided
    print(
        f"Fetching real-time data for {source} with source_id {source_id} since {since}"
    )
    real_time_data = []
    if since:

        data = load_historical_data(
            source, source_id, since, None
        )  # returns list of dicts/objects
    else:
        data = load_historical_data(
            source, source_id, None, None
        )  # returns list of dicts/objects
    for idx, row in data.iterrows():
        # 'idx' is now the 'time' index
        # add some some hours to the timestamp
        real_time_data.append(
            RealTimeDataPoint(timestamp=idx.isoformat(), value=row["value"])
        )

    return real_time_data


@app.get("/api/forecasted/{source}", response_model=List[ForecastedDataPoint])
def query_forecasted_data(
    source: str, source_id: str = None, start: str = None, end: str = None
):
    """
    Queries forecasted data for a given source and optional parameters.
    Args:
        source (str): The source of the forecasted data.
        source_id (str, optional): The ID of the source. Defaults to None.
        start (str, optional): The start date for the forecasted data in ISO format. Defaults to None.
        end (str, optional): The end date for the forecasted data in ISO format. Defaults to None.
    Returns:
        list: A list of ForecastedDataPoint objects containing the forecasted data.
    Raises:
        HTTPException: If there is an error in querying the forecasted data.
    """
    # type of start and end checking
    try:
        dataframe = load_forecasted_data(
            source, source_id, start, end
        )  # returns list of dicts/objects

        forecasted_data = []
        for idx, row in dataframe.iterrows():
            # 'idx' is now the 'time' index
            forecasted_data.append(
                ForecastedDataPoint(
                    timestamp=idx.isoformat(),
                    trend=row["trend"],
                    yhat_lower=row["yhat_lower"],
                    yhat_upper=row["yhat_upper"],
                    trend_lower=row["trend_lower"],
                    trend_upper=row["trend_upper"],
                    additive_terms=row["additive_terms"],
                    additive_terms_lower=row["additive_terms_lower"],
                    additive_terms_upper=row["additive_terms_upper"],
                    daily=row["daily"],
                    daily_lower=row["daily_lower"],
                    daily_upper=row["daily_upper"],
                    multiplicative_terms=row["multiplicative_terms"],
                    multiplicative_terms_lower=row["multiplicative_terms_lower"],
                    multiplicative_terms_upper=row["multiplicative_terms_upper"],
                    yhat=row["yhat"],
                )
            )
        return forecasted_data

    except Exception as e:
        print(f"Error in forecasted endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/historical/{source}", response_model=List[HistoricalDataPoint])
def query_historical_data(
    source: str,
    source_id: str = None,
    start: str = None,
    end: str = None,
    top: int = 50,
):
    """
    Queries historical data from a specified source within a given time range.
    Args:
        source (str): The source from which to query historical data.
        source_id (str, optional): The identifier for the specific source. Defaults to None.
        start (str, optional): The start time for the query in ISO 8601 format. Defaults to None.
        end (str, optional): The end time for the query in ISO 8601 format. Defaults to None.
    Returns:
        list: A list of HistoricalDataPoint objects containing the timestamp and value.
    Raises:
        HTTPException: If an error occurs while querying the historical data.
    """

    # type of start and end checking
    try:
        dataframe = load_historical_data(
            source, source_id, start, end, top
        )  # returns list of dicts/objects

        historical_data = []
        for idx, row in dataframe.iterrows():
            # 'idx' is now the 'time' index
            historical_data.append(
                HistoricalDataPoint(timestamp=idx.isoformat(), value=row["value"])
            )
        return historical_data

    except Exception as e:
        print(f"Error in historical_data endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/source-ids/{source}", response_model=List[str])
def query_ids(source: str):
    """
    Query the database to retrieve available source IDs for the given source type.
    Args:
        source (str): The type of source for which to retrieve available IDs.
    Returns:
        list: A list of available source IDs for the given source type.
    """

    # Query the database to retrieve available source IDs for the given source type
    # For example:
    available_ids = query_source_ids(source)  # Implement this function
    return available_ids


@app.get("/api/device-status", response_model=DeviceCounts)
def query_device_counts():
    """
    Queries the number of devices for each type and returns a DeviceCounts object.
    Returns:
        DeviceCounts: An object containing the counts of solar and wind devices.
    """

    # TODO: Add other types if needed
    solar = len(query_source_ids("solar"))
    wind = len(query_source_ids("wind"))
    return DeviceCounts(solar=solar, wind=wind)


@app.post("/api/optimize", response_model=List[Dict[str, Any]])
def optimize_strategy():
    """
    Optimizes the dispatch strategy
    Args:
    Returns:
        pd.DataFrame: A DataFrame containing the optimization results.
    """
    if not batteries:
        raise HTTPException(
            status_code=400, detail="No batteries available for optimization"
        )

    battery_list = list(batteries.values())
    try:
        result_df = optimize(battery_list)
        return result_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# # Database connection details from environment variables
# POSTGRES_USER = os.getenv("POSTGRES_USER", "gmpal")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgresso")
# POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
# TIMESCALEDB_HOST = os.getenv("TIMESCALEDB_HOST", "timescaledb.vpp.local")
# POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


# # Create a connection pool (for example purposes, adjust as needed)
# @app.on_event("startup")
# async def startup():
#     app.state.db_pool = await asyncpg.create_pool(
#         user=POSTGRES_USER,
#         password=POSTGRES_PASSWORD,
#         database=POSTGRES_DB,
#         host=TIMESCALEDB_HOST,
#         port=POSTGRES_PORT,
#     )


# @app.on_event("shutdown")
# async def shutdown():
#     await app.state.db_pool.close()


# @app.get("/health/db")
# async def health_check():
#     try:
#         async with app.state.db_pool.acquire() as connection:
#             # Execute a lightweight query
#             result = await connection.fetchval("SELECT 1;")
#             if result == 1:
#                 return {"status": "ok", "message": "Database connectivity is healthy."}
#             else:
#                 raise HTTPException(
#                     status_code=500, detail="Unexpected database response."
#                 )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Database connectivity error: {str(e)}"
#         )
