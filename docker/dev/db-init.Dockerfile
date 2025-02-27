FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

ENV TIMESCALEDB_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV MLFLOW_TRACKING_URI=http://localhost:5000
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092


RUN pip install --no-cache-dir pandas psycopg2-binary kafka-python
COPY ./backend ./backend
COPY ./entrypoints/db-init.sh ./db-init.sh
RUN chmod +x ./db-init.sh

ENTRYPOINT ["./db-init.sh"]

