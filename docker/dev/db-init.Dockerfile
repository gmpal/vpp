FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pandas psycopg2-binary kafka-python

COPY ./backend ./backend
COPY ./entrypoints/db-init.sh ./db-init.sh

RUN chmod +x ./db-init.sh
ENTRYPOINT ["./db-init.sh"]

