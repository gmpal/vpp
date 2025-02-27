#mlflow.Dockerfile
FROM python:3.10-slim

# Install dependencies
RUN pip install mlflow psycopg2-binary

# Set working directory
WORKDIR /app

# Run MLflow server
CMD ["mlflow", "server", \
    "--host", "0.0.0.0", \
    "--port", "5000", \
    "--gunicorn-opts", "--log-level debug"]


