#!/bin/sh
# set -e

# Run initialization (e.g., create Kafka topics)
# python create_topics.py

# Then start your main application


exec uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
