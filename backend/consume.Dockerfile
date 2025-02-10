FROM python:3.8-slim
WORKDIR /app

RUN apt-get update && apt-get install -y dnsutils && rm -rf /var/lib/apt/lists/*


RUN pip install kafka-python pandas numpy psycopg2-binary
COPY . /app
# The consumer service will run kafka_consume_centralized() as the main process.

# Set environment variables if needed. For example, Kafka bootstrap servers.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV KAFKA_BOOTSTRAP_SERVERS=kafka-service.vpp.local.vpp.local:9092
ENV TIMESCALEDB_HOST=172.31.32.54
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=gmpal
ENV POSTGRES_PASSWORD=postgresso

CMD ["python", "consume.py"]
