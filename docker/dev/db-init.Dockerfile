FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY ./backend ./backend
COPY ./entrypoints/db-init.sh ./db-init.sh

RUN chmod +x ./db-init.sh
ENTRYPOINT ["./db-init.sh"]
