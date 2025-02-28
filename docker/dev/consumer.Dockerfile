FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y dnsutils netcat-openbsd && rm -rf /var/lib/apt/lists/*
RUN pip install kafka-python pandas numpy psycopg2-binary

COPY ./backend ./backend
COPY ./entrypoints/consume.sh /app/consume.sh

RUN chmod +x /app/consume.sh
ENTRYPOINT ["/app/consume.sh"]
