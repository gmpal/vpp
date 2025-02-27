#!/bin/bash
export PYTHONPATH=/app:$PYTHONPATH
# In consumer.sh
until nc -z kafka 9092; do
  echo "Waiting for Kafka to be ready..."
  sleep 2
done
python /app/backend/src/streaming/communication.py