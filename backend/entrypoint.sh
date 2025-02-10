#!/bin/sh
set -e

# Run initialization (e.g., create Kafka topics)
python create_topics.py

# Then start your main application
exec uvicorn app:app --host 0.0.0.0 --port 8000
