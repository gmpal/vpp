# Backend Dockerfile: backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.8-slim


# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TIMESCALEDB_HOST=timescaledb
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://mlflow:5000

ENV KAFKA_BOOTSTRAP_SERVERS=kafka-service.vpp.local.vpp.local:9092

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project
COPY backend ./backend
COPY create_topics.py .

COPY config.ini .

# Expose the port your backend runs on (e.g., 8000 for Flask/Django)
EXPOSE 8000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]