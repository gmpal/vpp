#!/bin/bash
set -e
export PYTHONPATH=/app:$PYTHONPATH
until nc -z kafka 29092; do
  echo "Waiting for Kafka to be ready..."
  sleep 2
done
echo "Kafka port is open, waiting for Kafka to be fully ready..."
sleep 15
python /app/backend/src/streaming/create_topics.py
python /app/backend/src/streaming/start.py
