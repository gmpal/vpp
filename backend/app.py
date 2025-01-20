# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel

from src.db import (
    load_from_db,
    load_historical_data,
    query_source_ids,
    load_forecasted_data,
)

RENEWABLES = ["solar", "wind"]  # scalable for more renewables

app = FastAPI()

# Configure CORS if your frontend is on a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/forecasted/{source}", response_model=List[ForecastedDataPoint])
def forecasted_data(
    source: str, source_id: str = None, start: str = None, end: str = None
):
    """
    Fetches historical data for a source.
    If renewable, provide the source_id.
    Optionally filter by a start and end time.
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
def historical_data(
    source: str, source_id: str = None, start: str = None, end: str = None
):
    """
    Fetches historical data for a source.
    If renewable, provide the source_id.
    Optionally filter by a start and end time.
    """
    # type of start and end checking
    try:
        dataframe = load_historical_data(
            source, source_id, start, end
        )  # returns list of dicts/objects
        print(dataframe)
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
def get_source_ids(source: str):
    # Query the database to retrieve available source IDs for the given source type
    # For example:
    available_ids = query_source_ids(source)  # Implement this function
    return available_ids


@app.get("/api/realtime-data")
def realtime_data():
    """
    Endpoint to fetch real-time data.
    This function calls load_from_db() to retrieve data from the database,
    processes it, and returns a JSON object with the latest values.
    """
    data = load_from_db()

    latest_data = {}
    for key, value in data.items():
        if key == "renewables":
            for renewable, renewable_dict in value.items():
                for source_id, source_data in renewable_dict.items():
                    # Process renewable data
                    pass
        else:
            # Process load and market data
            pass

    # For example, suppose we take the first renewable source's latest value:
    if data["renewables"]:
        # Get the first renewable type and first source within that type
        first_renewable_type = next(iter(data["renewables"]))
        sources = data["renewables"][first_renewable_type]
        if sources:
            first_source_id = next(iter(sources))
            # Get the latest value from the series
            series = sources[first_source_id]
            if not series.empty:
                latest_data["generation"] = series.iloc[-1]  # Example usage

    # Similarly, you can extract values for consumption and storageLevel
    # using data["load"] and data["market"], adapting to your use case.
    print(latest_data)
    return latest_data
