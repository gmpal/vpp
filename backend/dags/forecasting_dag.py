from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import os

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "forecasting_dag",
    default_args=default_args,
    description="A simple DAG to train a Prophet model and forecast",
    schedule_interval="@daily",  # run daily, for example
    catchup=False,
)

def _train_model():
    from train_forecast import train_and_log_model
    train_and_log_model(run_name="prophet_forecast_daily", tune=False)

def _forecast_model():
    from forecast_and_save import forecast_and_save
    forecast_and_save(horizon=24)

with dag:
    train_task = PythonOperator(
        task_id="train_model",
        python_callable=_train_model
    )

    forecast_task = PythonOperator(
        task_id="forecast_model",
        python_callable=_forecast_model
    )

    # chain the tasks: train -> forecast
    train_task >> forecast_task
