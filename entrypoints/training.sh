#!/bin/bash
export PYTHONPATH=/app:$PYTHONPATH
#!/bin/bash
echo "Waiting for TimescaleDB to be ready..."
until nc -z timescaledb 5432; do
    echo "Waiting for TimescaleDB..."
    sleep 2
done

echo "Waiting for MLflow to be ready..."
until nc -z mlflow 5000; do
    echo "Waiting for MLflow..."
    sleep 2
done
python /app/backend/src/pipelines/training.py