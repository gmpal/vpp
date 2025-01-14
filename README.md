# vpp_forecasting_optimization
Forecasting &amp; Optimizing a Virtual Power Plant Portfolio

Postegresql - TimescaleDB setup

Chcek this https://docs.timescale.com/self-hosted/latest/install/installation-docker/ and then
```
-- Connect to PostgreSQL using psql or another client
CREATE DATABASE my_timeseries_db;
\c my_timeseries_db
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE power_data (
    time        TIMESTAMPTZ       NOT NULL,
    solar_power DOUBLE PRECISION,
    wind_power  DOUBLE PRECISION,
    load_power  DOUBLE PRECISION,
    net_power   DOUBLE PRECISION
);

-- Convert the table into a hypertable for optimized time-series data
SELECT create_hypertable('power_data', 'time');


```