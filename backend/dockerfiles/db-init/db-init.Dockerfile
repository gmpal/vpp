FROM python:3.8-slim
WORKDIR /app

ENV TIMESCALEDB_HOST=timescaledb
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgresso
ENV KAFKA_BOOTSTRAP_SERVERS=kafka-service.vpp.local.vpp.local:9092


RUN pip install --no-cache-dir pandas psycopg2-binary kafka-python
COPY data ./data
COPY src ./src
COPY config.ini .
COPY db-init.py . 
CMD ["python", "db-init.py"]
