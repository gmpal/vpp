# My Forecasting Project

## Overview
This project uses **Apache Airflow** to orchestrate a daily forecasting pipeline:
- Loads historical data from DB (`db_utils.py`)
- Trains a **Prophet** model, logs metrics/artifacts to **MLflow** (`train_forecast.py`)
- Generates 24-hour forecasts, saves results to DB (`forecast_and_save.py`)

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```