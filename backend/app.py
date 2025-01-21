# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import random
import pandas as pd

from src.db import (
    load_from_db,
    load_historical_data,
    query_source_ids,
    load_forecasted_data,
)

RENEWABLES = ["solar", "wind"]  # scalable for more renewables
COUNTER = 0

app = FastAPI()

# Configure CORS if your frontend is on a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed for production
    allow_credentials=True,
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
    source: str, source_id: str = None, start: str = None, end: str = None
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
            source, source_id, start, end
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
