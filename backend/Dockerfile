# Backend Dockerfile: backend/Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
COPY src ./src
COPY data ./data
COPY app.py .
COPY config.ini .

# Expose the port your backend runs on (e.g., 8000 for Flask/Django)
EXPOSE 8000

# Define the default command to run your backend application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
