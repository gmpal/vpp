# Use a lightweight Python base image
FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc git netcat-openbsd

# Create a working directory
WORKDIR /app

ENV TIMESCALEDB_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://localhost:5000

# Copy and install dependencies
COPY requirements/requirements-forecasting.txt .
RUN pip install --no-cache-dir -r requirements-forecasting.txt

# Copy all your source code (including train_pipeline.py, src/ folder, etc.)
COPY ./backend ./backend

COPY ./entrypoints/training.sh ./training.sh
RUN chmod +x ./training.sh
ENTRYPOINT ["./training.sh"]
