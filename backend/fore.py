from src.forecasting import forecast_and_save
from src.db import reset_forecast_tables


if __name__ == "__main__":
    reset_forecast_tables()
    forecast_and_save()
