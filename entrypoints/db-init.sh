#!/bin/bash
export PYTHONPATH=/app:$PYTHONPATH
until nc -z kafka 9092; do
  echo "Waiting for Kafka to be ready..."
  sleep 2
done
python /app/backend/src/streaming/create_topics.py
python /app/backend/src/streaming/start.py