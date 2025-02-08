# Use a lightweight Python base image
FROM python:3.9-slim

RUN apt-get update && apt-get install -y libpq-dev gcc git

# Create a working directory
WORKDIR /app

# Set env variables for DB or MLflow if needed
ENV TIMESCALEDB_HOST=172.31.5.84
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://vpp-mlflow-load-balancer-23407623.eu-central-1.elb.amazonaws.com

# Copy and install dependencies
COPY requirements-forecasting.txt .
RUN pip install --no-cache-dir -r requirements-forecasting.txt

# Copy all your source code (including train_pipeline.py, src/ folder, etc.)
COPY . /app

# Default command runs the training pipeline
CMD ["python", "train_pipeline.py"]
