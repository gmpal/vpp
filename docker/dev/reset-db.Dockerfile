# reset-db.Dockerfile is used to create a docker image that will reset the database to its initial state.
FROM python:3.10-slim
WORKDIR /app

ENV TIMESCALEDB_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso
ENV KAFKA_BOOTSTRAP_SERVERS=localhost:9092

RUN pip install --no-cache-dir pandas psycopg2-binary kafka-python
COPY backend ./backend

COPY ./entrypoints/reset_db.sh ./reset_db.sh
RUN chmod +x ./reset_db.sh
ENTRYPOINT ["./reset_db.sh"]
