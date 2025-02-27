# inference.Dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc git netcat-openbsd

WORKDIR /app

# Set env variables for DB or MLflow if needed
ENV TIMESCALEDB_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://localhost:5000

# Install dependencies
COPY ./requirements/requirements-forecasting.txt .
RUN pip install --no-cache-dir -r requirements-forecasting.txt

# Copy your entire backend code
COPY ./backend ./backend

# The command now runs the inference pipeline
COPY ./entrypoints/inference.sh /app/inference.sh
RUN chmod +x /app/inference.sh
ENTRYPOINT ["/app/inference.sh"]
