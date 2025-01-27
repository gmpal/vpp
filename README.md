# Virtual Power Plant (VPP) Project

## Overview
This project simulates a Virtual Power Plant (VPP) system, including synthetic data generation, forecasting, optimization, and database management. The system models energy generation from solar and wind sources, energy consumption (load), and market prices. It integrates with a Kafka-based communication pipeline for real-time data streaming and supports optimization of battery usage to minimize costs.

## Features

1. **Synthetic Data Generation**
   - Generate weather data (e.g., solar irradiance, wind speed, temperature) for wind and photovoltaic (PV) power generation.
   - Simulate renewable energy generation (solar and wind) and energy consumption (load) with realistic patterns and random noise.
   - Create synthetic market price data.

2. **Forecasting**
   - Use the Prophet model to forecast renewable generation, load, and market prices.
   - Perform hyperparameter optimization for forecasting models using Optuna.
   - Save forecasts to the database for later use.

3. **Battery Modeling**
   - Simulate battery behavior, including charging, discharging, and tracking state-of-charge (SOC).
   - Enforce constraints such as maximum charge/discharge rates and round-trip efficiency.

4. **Optimization**
   - Optimize battery operations to minimize costs by leveraging forecasted data.
   - Use PuLP to solve linear programming problems for battery scheduling, grid interactions, and renewable energy usage.

5. **Database Integration**
   - Manage data for renewable energy sources, load, market prices, and forecasts using TimescaleDB.
   - Support efficient data retrieval and storage with hypertables for time-series data.

6. **Kafka Communication**
   - Stream data from producers (renewables, load, market) to Kafka topics.
   - Consume data from Kafka and store it in the database for processing.

7. **Model Training**
   - Train and compare models for forecasting (Prophet, ARIMA, Random Forest, and N-BEATS).
   - Use MLflow to track experiments, metrics, and artifacts.

## File Structure

### 1. Synthetic Data Generation
- **`generation.py`**
  - Functions to generate weather data, renewable generation (wind, PV), synthetic load, and market prices.
  - Supports output to CSV for use by Kafka producers.

### 2. Forecasting
- **`forecasting.py`**
  - Load data from the database and use the Prophet model to forecast future values.
  - Save forecasts to the database.

- **`train_forecast.py`**
  - Train models (Prophet, ARIMA, Random Forest, N-BEATS) with hyperparameter optimization.
  - Evaluate models and log results to MLflow.

### 3. Battery Modeling
- **`battery.py`**
  - Battery class to simulate charging, discharging, and SOC tracking.
  - Includes efficiency and capacity constraints.

### 4. Optimization
- **`optimization.py`**
  - Optimize battery scheduling using PuLP to minimize costs.
  - Combine forecasted data with battery operations to determine optimal usage.

### 5. Database Management
- **`db.py`**
  - Functions to interact with TimescaleDB for storing and retrieving data.
  - Manage tables for renewables, load, market prices, and forecasts.
  - Reset tables and store battery states.

### 6. Kafka Communication
- **`communication.py`**
  - Produce data from CSV files to Kafka topics for streaming.
  - Consume data from Kafka topics and store it in the database.

### 7. Source Management
- **`sources.py`**
  - Create new data sources (wind or PV) and optionally connect them to Kafka producers.

### 8. Forecast and Save
- **`forecast_and_save.py`**
  - Generate forecasts using the Prophet model and save results to the database.

## Usage

### Prerequisites
- Python 3.8+
- Kafka cluster (for data streaming)
- TimescaleDB (for time-series data management)
- Required Python packages (install using `requirements.txt`)

### Steps

1. **Set Up the Environment**
   - Install dependencies using:
     ```bash
     pip install -r requirements.txt
     ```
   - Configure database and Kafka settings in `config.ini`.

2. **Generate Synthetic Data**
   - Run `generation.py` to generate weather, renewable generation, load, and market price data.
   - Example:
     ```bash
     python generation.py
     ```

3. **Run Kafka Producers and Consumers**
   - Use `communication.py` to produce data to Kafka topics.
   - Example:
     ```bash
     python communication.py
     ```

4. **Train Models**
   - Use `train_forecast.py` to train forecasting models and log results to MLflow.
   - Example:
     ```bash
     python train_forecast.py
     ```

5. **Optimize Battery Operations**
   - Run `optimization.py` to determine optimal battery schedules.
   - Example:
     ```bash
     python optimization.py
     ```

6. **Forecast and Save**
   - Use `forecast_and_save.py` to generate and save forecasts to the database.
   - Example:
     ```bash
     python forecast_and_save.py
     ```

## Key Components

### Configuration
- **`config.ini`**
  - Specify database credentials, Kafka settings, and generation parameters.

### Database Schema
- Tables for renewable sources, load, market prices, and forecasts.
- Hypertables for efficient time-series storage.

### Kafka Topics
- **`solar-topic`**: Solar power data.
- **`wind-topic`**: Wind power data.
- **`load-topic`**: Load data.
- **`market-topic`**: Market price data.

## Future Work
- Integrate real-world data sources.
- Implement additional forecasting models.
- Enhance optimization with multi-objective approaches.
- Deploy on cloud platforms for scalability.

## Contributors
- Author: [Your Name]
- Contact: [Your Email]

## License
This project is licensed under the MIT License. See the LICENSE file for details.

