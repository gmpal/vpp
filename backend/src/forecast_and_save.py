import mlflow
import pandas as pd
from prophet import Prophet
from db_utils import save_forecast_to_db

"""
If you store your Prophet model differently (e.g., mlflow.sklearn.log_model(model) vs. mlflow.pyfunc.log_model), the load API differs. Check MLflow docs.
"""


def load_production_model(model_name="MyProphetModel"):
    """
    Example: load the 'Production' version of your model from MLflow Model Registry,
    or load by run_id / path. Adjust as needed.
    """
    model_uri = f"models:/{model_name}/Production"
    # If you use the 'Production' stage in the Model Registry, this is how to load:
    model = mlflow.pyfunc.load_model(model_uri)
    return model


def forecast_and_save(model=None, horizon=24):
    """
    Generate a forecast for the next 'horizon' hours, store in DB.
    """
    if model is None:
        model = load_production_model()

    # Prophet requires an actual Prophet object, so if you're storing the
    # model as a generic PyFunc, you might need a different loading approach
    # e.g. mlflow.sklearn.load_model(...) or a custom model type.

    # For demonstration, let's assume 'model' is a Prophet instance
    # or has a .make_future_dataframe() method.
    future = model.make_future_dataframe(periods=horizon, freq="H")
    fcst = model.predict(future)

    # We'll keep only the last 'horizon' rows
    fcst_res = fcst.tail(horizon).set_index("ds")
    fcst_res = fcst_res[["yhat"]]

    # Save to DB
    save_forecast_to_db(fcst_res)
    print("Forecast saved to DB")


if __name__ == "__main__":
    forecast_and_save()
