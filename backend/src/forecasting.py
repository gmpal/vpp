import pandas as pd
from src.db import load_from_db, save_forecasts_to_db
from prophet import Prophet

RENEWABLES = [
    "solar",
    "wind",
]  # scalable for more renewables TODO: avoid redundancy with db.py


# Function to prepare data for Prophet and forecast
def forecast_with_prophet(time_series_df, forecast_steps=24, freq="h"):
    """
    time_series_df: DataFrame with datetime index and one value column.
    forecast_steps: Number of time steps to forecast.
    freq: Frequency string (e.g., 'H' for hourly).

    """
    # Reset index and rename columns for Prophet
    df = time_series_df.reset_index()
    df.columns = ["ds", "y"]

    # ValueError: Column ds has timezone specified, which is not supported. Remove timezone.
    df["ds"] = df["ds"].dt.tz_localize(None)
    # Initialize and fit Prophet model
    model = Prophet()
    model.fit(df)

    # Create a future dataframe for forecasting
    future = model.make_future_dataframe(periods=forecast_steps, freq=freq)

    # Forecast future values
    forecast = model.predict(future)
    # filter out last forecast_steps
    return forecast.tail(forecast_steps)


def forecast_and_save(forecast_steps: int = 24, frequency: str = "s"):
    """
    Data Format:
    data_from_db = {"renewables": {renewable1: {source_id_1: pd.Series, source_id_1: pd.Series,...}, renewable2: {}, ... }, "load": pd.Series, "market_price": pd.Series}

    forecasted = {"renewables": {renewable1: {source_id_1: pd.Dataframe, source_id_1: pd.Dataframe,...}, renewable2: {}, ... }, "load": pd.Dataframe, "market_price": pd.Dataframe}
    """
    data_from_db = load_from_db()

    # same structure as renewables dict
    forecasted = {}
    for key, value in data_from_db.items():
        if key == "renewables":
            forecasted[key] = {}
            for renewable, renewable_dict in value.items():
                forecasted[key][renewable] = {}
                for source_id, source_data in renewable_dict.items():
                    forecasted[key][renewable][source_id] = forecast_with_prophet(
                        source_data, forecast_steps, frequency
                    )
        else:  # forecast load and market_price
            print(f"Forecasting {key}")
            forecasted[key] = forecast_with_prophet(value, forecast_steps, frequency)

    # print from and to of this data
    save_forecasts_to_db(forecasted)


if __name__ == "__main__":
    forecast_and_save()
