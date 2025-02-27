FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y dnsutils netcat-openbsd && rm -rf /var/lib/apt/lists/*

RUN pip install kafka-python pandas numpy psycopg2-binary
COPY ./backend ./backend

# The consumer service will run kafka_consume_centralized() as the main process.

# Set environment variables if needed. For example, Kafka bootstrap servers.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TIMESCALEDB_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://localhost:5000

ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Copy with explicit destination
COPY ./entrypoints/consume.sh /app/consume.sh
RUN chmod +x /app/consume.sh
ENTRYPOINT ["/app/consume.sh"]
