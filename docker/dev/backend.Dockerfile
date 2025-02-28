# Backend Dockerfile: backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/requirements-backend.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-backend.txt

# Copy the project
COPY ./backend ./backend

# Expose the port your backend runs on (e.g., 8000 for Flask/Django)
EXPOSE 8000

COPY ./entrypoints/backend.sh ./backend.sh
RUN chmod +x ./backend.sh
ENTRYPOINT ["./backend.sh"]