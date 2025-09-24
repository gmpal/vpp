# Virtual Power Plant (VPP) Simulation

[![Run Pytest Suite](https://github.com/gmpal/vpp/workflows/Run%20Pytest%20Suite/badge.svg)](https://github.com/gmpal/vpp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modular, containerized microservices system for simulating a Virtual Power Plant. The project integrates synthetic data generation, real-time data streaming with Kafka, automated machine learning forecasting with MLflow, and linear optimization with PuLP to emulate energy management decisions for distributed energy resources.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [API Overview](#api-overview)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

This project simulates a **Virtual Power Plant (VPP)** that leverages synthetic data and modular microservices to emulate a real-world distributed energy system. The core idea is to generate synthetic data representing various energy sources and grid parameters, then process, forecast, and optimize energy management decisions in near real-time.

The system is fully containerized using Docker, enabling scalable deployments and simplified local development with Docker Compose.

## Key Features

-   **Synthetic Data Generation**: Generates realistic time-series data for solar (`pvlib`), wind (`windpowerlib`), grid load, and market prices.
-   **Real-Time Data Streaming**: Streams generated data via Kafka producers to a central consumer, simulating live data feeds from distributed assets.
-   **Time-Series Database**: Ingests and stores all historical and forecasted data in a TimescaleDB instance for efficient querying and analysis.
-   **Automated ML Forecasting Pipelines**:
    -   **Training Pipeline**: Runs on a schedule (every 60 mins) to perform time-series cross-validation, compare models (e.g., RandomForest), and log experiments, metrics, and models to **MLflow**.
    -   **Inference Pipeline**: Runs frequently (every 5 mins) to load the best models from the MLflow Registry and generate 30-step-ahead forecasts.
-   **Linear Optimization**: Utilizes **PuLP** to solve an optimization problem that determines the most profitable strategy for battery charging/discharging and grid energy trading based on forecasts.
-   **Interactive Frontend**: A React-based UI allows users to add new energy sources and batteries on-the-fly, and visualize historical data, forecasts, and optimization results.
-   **Modular Microservices**: The entire system is broken down into independent, containerized services (backend, frontend, database, Kafka, pipelines) for scalability and maintainability.

## System Architecture

The VPP simulation is composed of several Dockerized microservices that communicate via REST APIs and Kafka messaging:

-   **`frontend`**: A React application providing the user interface for monitoring, managing resources, and visualizing data.
-   **`backend`**: A FastAPI application that serves the REST API, handles requests from the frontend, and interacts with the database and MLflow.
-   **`db-init`**: An initialization service that sets up the database schema, loads an initial batch of historical data, and starts the Kafka producers to stream the remaining synthetic data.
-   **`consumer`**: A centralized Kafka consumer that listens to all data topics (`solar`, `wind`, `load`, `market`) and writes the incoming data to TimescaleDB.
-   **`training-pipeline`**: A scheduled task that runs periodically to train forecasting models on the latest data from TimescaleDB and register the best models in MLflow.
-   **`inference-pipeline`**: A scheduled task that fetches the latest models from MLflow to generate and save new forecasts to the database.
-   **Infrastructure**:
    -   **`timescaledb`**: The core time-series database for storing all data.
    -   **`kafka` & `zookeeper`**: The messaging backbone for real-time data streaming.
    -   **`mlflow`**: The MLOps platform for experiment tracking, model storage, and model registry.

## Technology Stack

| Category              | Technology                                       | Purpose                                                 |
| --------------------- | ------------------------------------------------ | ------------------------------------------------------- |
| **Backend**           | Python, FastAPI                                  | REST API development and business logic.                |
| **Frontend**          | React, TypeScript, Material-UI, Chart.js         | Interactive user interface and data visualization.      |
| **Database**          | TimescaleDB (PostgreSQL)                         | Storing and querying time-series data.                  |
| **Data Streaming**    | Apache Kafka                                     | Real-time messaging between data sources and consumer.  |
| **ML/Forecasting**    | Scikit-learn, pmdarima, Prophet                  | Time-series forecasting models.                         |
| **MLOps**             | MLflow                                           | Experiment tracking, model registry, and logging.       |
| **Optimization**      | PuLP                                             | Linear programming for energy dispatch optimization.    |
| **Containerization**  | Docker, Docker Compose                           | Containerizing and orchestrating all microservices.     |
| **Data Generation**   | `pvlib`, `windpowerlib`                          | Creating synthetic solar and wind energy data.          |

## Prerequisites

-   Docker & Docker Compose
-   Python 3.8+ (for running scripts outside Docker)
-   Node.js (for frontend development outside Docker)

## Installation and Setup

The entire system can be set up and run locally using Docker Compose.

1.  **Start Core Infrastructure:**
    Launch the database, Kafka, and MLflow services in detached mode.
    ```bash
    docker-compose up -d timescaledb zookeeper kafka mlflow
    ```

2.  **Start the Data Consumer:**
    Start the consumer service so it's ready to receive messages from the producers.
    ```bash
    docker-compose up -d consumer
    ```
    *Wait a few moments for the infrastructure and consumer to initialize.*

3.  **Initialize Database and Start Streaming:**
    This command runs the `db-init` service, which populates the database with initial data and starts streaming the rest via Kafka producers. The `--profile init` flag activates the service defined in the `init` profile.
    ```bash
    docker-compose --profile init up db-init
    ```
    *(Run this command without `-d` to see the logs and confirm that data is being produced).*

4.  **Start Application Services:**
    Launch the backend API and the frontend UI.
    ```bash
    docker-compose up -d backend frontend
    ```

5.  **Run Scheduled Tasks (Manually):**
    The training and inference pipelines are defined under the `task` profile and can be run on-demand for development or testing.
    ```bash
    # Run the training pipeline
    docker-compose --profile task up --no-deps training

    # Run the inference pipeline
    docker-compose --profile task up --no-deps inference
    ```

Once all services are running, you can access the different components:
-   **Frontend UI**: `http://localhost:3000`
-   **Backend API Docs**: `http://localhost:8000/docs`
-   **MLflow UI**: `http://localhost:5000`

## Usage

After starting the services, the system will begin simulating the VPP:

1.  **Data Generation & Streaming**: The `db-init` service will continuously produce new data points for all sources and push them to Kafka topics.
2.  **Data Ingestion**: The `consumer` service will ingest this data and save it to TimescaleDB.
3.  **Forecasting**: The `training` and `inference` pipelines will run automatically on their schedules (or you can trigger them manually as shown above) to keep the forecasts up-to-date.
4.  **Interacting with the UI**:
    -   Navigate to `http://localhost:3000`.
    -   **Dashboard**: Add new solar/wind generators or batteries. View the current status of all devices.
    -   **Renewables/Grid/Market Tabs**: Visualize historical and forecasted data for different sources.
    -   **Optimization Tab**: Trigger the optimization engine and view the recommended battery and grid dispatch strategy.

## API Overview

The backend provides a RESTful API for interacting with the VPP. Key endpoints include:

-   `GET /health`: Health check for the backend service.
-   `GET /api/batteries`: Get the status of all batteries.
-   `POST /api/batteries`: Add a new battery to the system.
-   `POST /api/batteries/{battery_id}/charge`: Charge a specific battery.
-   `GET /api/add-source?source_type={type}`: Add a new renewable energy source (`solar` or `wind`).
-   `GET /api/historical/{source}`: Query historical data for a source (e.g., `solar`, `load`).
-   `GET /api/forecasted/{source}`: Query forecasted data for a source.
-   `POST /api/optimize`: Run the optimization algorithm and get the dispatch strategy.

For a full list of endpoints and their parameters, see the auto-generated Swagger documentation at `http://localhost:8000/docs`.

## Troubleshooting

-   **Service Fails to Start**: Check the logs for the specific service using `docker-compose logs <service_name>`.
-   **No Data in Frontend**:
    -   Ensure the `db-init` service ran successfully and is producing messages.
    -   Check the `consumer` logs to see if it's receiving messages and writing to the database.
    -   Verify the `backend` can connect to `timescaledb`.
-   **MLflow UI is Empty**: Make sure the `training` pipeline has run at least once. Trigger it manually if needed.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs or feature requests.