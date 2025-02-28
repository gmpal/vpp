![Tests](https://github.com/gmpal/vpp/workflows/Run%20Pytest%20Suite/badge.svg)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/gmpal/ecfd0b8a247e4da2abafbdc142d7d01b/raw/coverage.json)

## Project Description

This project simulates a **Virtual Power Plant (VPP)** that leverages synthetic data and modular microservices to emulate a real-world distributed energy system. The core idea is to generate synthetic data representing various energy sources and grid parameters, then process, forecast, and optimize energy management decisions in near real time.

### Key Components

1. **Synthetic Data Generation & Ingestion:**
   - **Synthetic Data Sources:**  
     Using specialized libraries, synthetic weather data (for solar and wind generation), grid load, and market price data are generated to mimic real operating conditions.
   - **Data Streaming & Storage:**  
     A dedicated **db-init** service stores a portion of the generated files locally. The remaining data is streamed in real time via Kafka—each source having its own producer—to simulate live data feeds. A centralized consumer then ingests this data and writes it into a TimescaleDB database for further processing.

2. **Forecasting Pipeline:**
   - **Training Pipeline:**  
     Scheduled to run every 60 minutes, the training pipeline performs time series cross-validation on the incoming data. It compares multiple univariate machine learning models for each data source and selects the best-performing model, optionally tuning hyperparameters. All experiments and model performance metrics are logged in MLflow for tracking and reproducibility.
   - **Inference Pipeline:**  
     Running every 5 minutes, the inference pipeline retrieves the best model for each source and generates 30-step ahead forecasts. This simulates a scenario where, for instance, a forecast generated at 6 pm is used to predict the day-ahead market conditions.

3. **Modularity & Extensibility:**
   - **Adding New Sources:**  
     The frontend allows users to manually add new data sources, making it easy to extend the system.
   - **Battery Module:**  
     A separate module is dedicated to managing batteries. Users can add battery configurations that are then integrated into the overall optimization process.
   - **Additional Streams:**  
     In addition to generation data, the system simulates grid load and market price streams to reflect broader system dynamics.

4. **Optimization Module:**
   - Using PuLP, the system performs a linear optimization that combines forecast data with battery state information. The optimization module determines the best strategy for the next 30 time steps—providing decisions on grid buying/selling as well as battery charge/discharge—to maximize efficiency and profitability for the VPP.

The overall architecture is fully containerized using Docker, enabling scalable deployments on AWS and simplifying local development with tools like Docker Compose.

---

## README.md

```markdown
# Virtual Power Plant (VPP) Simulation System

A modular, containerized microservices system for simulating a Virtual Power Plant. The project integrates synthetic data generation, real-time data streaming, forecasting pipelines, and an optimization module to emulate energy management decisions for distributed energy resources.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
  - [Synthetic Data Generation & Ingestion](#synthetic-data-generation--ingestion)
  - [Forecasting Pipeline](#forecasting-pipeline)
  - [Optimization Module](#optimization-module)
  - [Frontend & Battery Management](#frontend--battery-management)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project simulates a Virtual Power Plant that uses synthetic data to mimic real-time energy production and consumption. The system streams generated data via Kafka to a centralized TimescaleDB and processes it through dedicated forecasting pipelines. The forecasts are then fed into an optimization module (using PuLP) to determine optimal energy management strategies—deciding when to buy, sell, charge, or discharge batteries.

## Architecture

The system is built as a collection of Dockerized microservices:

- **db-init Service:**  
  Initializes the database, stores part of the synthetic data locally, and streams the remaining data to simulate real-time ingestion via Kafka.

- **Backend Service:**  
  Handles API requests, integrates with MLflow for experiment tracking, and communicates with the database and Kafka.

- **Frontend Service:**  
  A user interface built with React, allowing manual addition of data sources and batteries.

- **Forecasting Pipelines:**  
  - **Training Pipeline:** Runs every 60 minutes to perform time series cross-validation, compare multiple models, and log results in MLflow.
  - **Inference Pipeline:** Runs every 5 minutes to perform 30-step ahead forecasts for the day-ahead market (e.g., forecasts generated at 6 pm).

- **Optimization Module:**  
  Uses forecasted data and battery states to perform linear optimization with PuLP, outputting strategies for grid interactions and battery management over the next 30 time steps.

## Components

### Synthetic Data Generation & Ingestion

- **Data Generation:**  
  Synthetic weather data, wind and solar generation, grid load, and market prices are generated using libraries like `pvlib` and `windpowerlib`. Each data source is uniquely identified.
  
- **Data Ingestion:**  
  The `db-init` service partially stores the generated files and streams the remainder via Kafka (with one producer per source). A centralized consumer writes the incoming data into a TimescaleDB database.

### Forecasting Pipeline

- **Training Pipeline:**  
  - Performs time series cross-validation.
  - Compares multiple univariate machine learning models (one per source).
  - Optionally tunes hyperparameters.
  - Logs all experiments and metrics in MLflow.
  - Scheduled to run every 60 minutes.

- **Inference Pipeline:**  
  - Retrieves the best-performing model for each source.
  - Generates 30-step ahead forecasts (e.g., for the next day-ahead market starting at 6 pm).
  - Scheduled to run every 5 minutes.

### Optimization Module

- **Purpose:**  
  Uses forecast data alongside battery states and market information to compute the optimal strategy using PuLP.
- **Output:**  
  Provides recommendations for grid buy/sell actions and battery charge/discharge schedules over the next 30 time steps.
- **Key Features:**  
  - Integrates forecasts from renewable sources, grid load, and market price.
  - Supports individual battery management.
  - Easily extensible for additional constraints or decision variables.

### Frontend & Battery Management

- **Frontend:**  
  A React-based UI that allows users to manually add new energy sources or battery configurations.
- **Battery Module:**  
  Manages battery information and integrates with the optimization module to ensure accurate state-of-charge tracking and scheduling.

## Prerequisites

- **Docker & Docker Compose:** For containerizing and orchestrating services.
- **Python 3.8/3.9:** For backend services and forecasting pipelines.
- **Node.js:** For building and running the frontend.
- **AWS Account:** For deploying services using AWS ECS, ECR, etc. (if desired).

## Installation and Setup

   ```bash
   docker-compose up --build
   ```
