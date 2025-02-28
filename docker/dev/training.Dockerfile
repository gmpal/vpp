# Use a lightweight Python base image
FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc git netcat-openbsd

# Create a working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements/requirements-forecasting.txt .
RUN pip install --no-cache-dir -r requirements-forecasting.txt

# Copy all your source code (including train_pipeline.py, src/ folder, etc.)
COPY ./backend ./backend

COPY ./entrypoints/training.sh ./training.sh
RUN chmod +x ./training.sh
ENTRYPOINT ["./training.sh"]
